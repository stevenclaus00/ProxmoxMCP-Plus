import json
from unittest.mock import Mock

import pytest

from proxmox_mcp.tools.containers import ContainerTools
from proxmox_mcp.tools.iso import ISOTools
from proxmox_mcp.tools.snapshots import SnapshotTools
from proxmox_mcp.tools.vm import VMTools


class _JobStore:
    def __init__(self):
        self.registered: list[dict[str, object]] = []

    def register_task(self, **kwargs):
        self.registered.append(kwargs)
        return {"job_id": f"job-{len(self.registered)}", **kwargs}


def test_get_vms_falls_back_to_node_scan_with_configured_cores():
    proxmox = Mock()
    proxmox.cluster.resources.get.side_effect = RuntimeError("cluster endpoint unavailable")
    proxmox.nodes.get.return_value = [{"node": "pve1"}]
    node_api = Mock()
    proxmox.nodes.return_value = node_api
    node_api.qemu.get.return_value = [
        {"vmid": 100, "name": "db", "status": "running", "mem": 256, "maxmem": 1024}
    ]
    node_api.qemu.return_value.config.get.return_value = {"cores": 4}

    response = VMTools(proxmox).get_vms()

    assert "db" in response[0].text
    assert "pve1" in response[0].text
    node_api.qemu.return_value.config.get.assert_called_once()


def test_create_vm_auto_detects_lvm_storage_and_registers_job():
    proxmox = Mock()
    node_api = Mock()
    proxmox.nodes.return_value = node_api
    node_api.qemu.return_value.config.get.side_effect = RuntimeError("does not exist")
    node_api.storage.get.return_value = [
        {"storage": "local", "content": "iso,vztmpl", "type": "dir"},
        {"storage": "local-lvm", "content": "images,rootdir", "type": "lvmthin"},
    ]
    node_api.qemu.create.return_value = "UPID:create-vm"
    job_store = _JobStore()

    response = VMTools(proxmox, job_store=job_store).create_vm(
        "pve1",
        "200",
        "worker",
        cpus=2,
        memory=2048,
        disk_size=20,
    )

    created = node_api.qemu.create.call_args.kwargs
    assert created["scsi0"] == "local-lvm:20,format=raw"
    assert created["net0"] == "virtio,bridge=vmbr0"
    assert "Job ID: job-1" in response[0].text
    assert job_store.registered[0]["retry_spec"]["kind"] == "vm.create"


def test_get_containers_include_stats_json_adds_raw_status_and_rrd_fallback():
    proxmox = Mock()
    proxmox.cluster.resources.get.return_value = [
        {"type": "lxc", "node": "pve1", "vmid": 101, "name": "web", "status": "running"}
    ]
    ct_api = proxmox.nodes.return_value.lxc.return_value
    ct_api.status.current.get.return_value = {"status": "running", "cpu": 0, "mem": 0, "maxmem": 0}
    ct_api.config.get.return_value = {"memory": 512, "cores": 2, "swap": 512}
    ct_api.rrddata.get.return_value = [{"cpu": 0.25, "mem": 134217728, "maxmem": 536870912}]

    response = ContainerTools(proxmox).get_containers(
        include_stats=True,
        include_raw=True,
        format_style="json",
    )
    payload = json.loads(response[0].text)

    assert payload[0]["name"] == "web"
    assert payload[0]["cpu_pct"] == 25.0
    assert payload[0]["mem_bytes"] == 134217728
    assert payload[0]["raw_status"]["status"] == "running"
    ct_api.rrddata.get.assert_called_once_with(timeframe="hour", ds="cpu,mem,maxmem")


def test_create_container_auto_detects_storage_and_omits_secret_retry_spec():
    proxmox = Mock()
    proxmox.cluster.resources.get.return_value = []
    proxmox.nodes.get.return_value = [{"node": "pve1"}]
    proxmox.storage.get.return_value = [
        {"storage": "slow-dir", "content": "rootdir", "type": "dir"},
        {"storage": "local-lvm", "content": "rootdir,images", "type": "lvmthin"},
    ]
    proxmox.nodes.return_value.lxc.create.return_value = "UPID:create-ct"
    job_store = _JobStore()
    tools = ContainerTools(proxmox, job_store=job_store)

    response = tools.create_container(
        "pve1",
        "201",
        "local:vztmpl/debian.tar.zst",
        password="secret",
        nesting=True,
        onboot=True,
    )

    created = proxmox.nodes.return_value.lxc.create.call_args.kwargs
    assert created["rootfs"] == "local-lvm:8"
    assert created["features"] == "nesting=1"
    assert created["onboot"] == 1
    assert job_store.registered[0]["retry_spec"] is None
    assert "Job ID: job-1" in response[0].text


def test_list_snapshots_skips_current_and_formats_snapshot_time():
    proxmox = Mock()
    snapshot_api = proxmox.nodes.return_value.qemu.return_value.snapshot
    snapshot_api.get.return_value = [
        {"name": "current"},
        {"name": "before-upgrade", "description": "stable", "snaptime": 1700000000, "vmstate": 1},
    ]

    response = SnapshotTools(proxmox).list_snapshots("pve1", "100")

    assert "before-upgrade" in response[0].text
    assert "current" not in response[0].text
    assert "RAM State: Included" in response[0].text


def test_rollback_snapshot_refuses_when_child_snapshots_exist():
    proxmox = Mock()
    snapshot_api = proxmox.nodes.return_value.qemu.return_value.snapshot
    snapshot_api.get.return_value = [
        {"name": "base"},
        {"name": "child", "parent": "base"},
    ]

    with pytest.raises(RuntimeError, match="newer child snapshots"):
        SnapshotTools(proxmox).rollback_snapshot("pve1", "100", "base")

    snapshot_api.return_value.rollback.post.assert_not_called()


def test_download_iso_includes_checksum_and_registers_retry_recipe():
    proxmox = Mock()
    storage_api = proxmox.nodes.return_value.storage.return_value
    download_api = storage_api.return_value
    download_api.post.return_value = "UPID:download"
    job_store = _JobStore()

    response = ISOTools(proxmox, job_store=job_store).download_iso(
        "pve1",
        "local",
        "https://example.test/debian.iso",
        "debian.iso",
        checksum="abc123",
        checksum_algorithm="sha512",
    )

    request = download_api.post.call_args.kwargs
    assert request["checksum-algorithm"] == "sha512"
    assert job_store.registered[0]["retry_spec"]["kind"] == "iso.download"
    assert "Checksum: SHA512" in response[0].text


def test_list_isos_filters_storage_content_by_node_and_storage():
    proxmox = Mock()
    proxmox.nodes.get.return_value = [{"node": "pve1"}, {"node": "pve2"}]
    node_api = proxmox.nodes.return_value
    node_api.storage.get.return_value = [
        {"storage": "local", "content": "iso,vztmpl"},
        {"storage": "backup", "content": "backup"},
    ]
    node_api.storage.return_value.content.get.return_value = [
        {"volid": "local:iso/debian.iso", "size": 1024},
    ]

    response = ISOTools(proxmox).list_isos(node="pve1", storage="local")

    assert "debian.iso" in response[0].text
    assert "local @ pve1" in response[0].text
    node_api.storage.return_value.content.get.assert_called_once_with(content="iso")
