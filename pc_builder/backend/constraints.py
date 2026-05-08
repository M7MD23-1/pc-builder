def normalize_purpose_name(purpose):
    text = str(purpose or "").strip()
    aliases = {
        "AI / ML Workstation": "AI Workstation",
        "AI/ML Workstation": "AI Workstation",
    }
    return aliases.get(text, text)


def cpu_mb_compatible(cpu, mb):
    return str(cpu.get("socket", "")).strip() == str(mb.get("socket", "")).strip()


def ram_mb_compatible(ram, mb):
    return str(ram.get("type", "")).strip().upper() == str(mb.get("ram_type", "")).strip().upper()


def storage_mb_compatible(storage, mb):
    iface = str(storage.get("interface", "")).strip().upper()
    if iface == "NVME":
        nvme_flag = str(mb.get("nvme_support", "")).strip().lower() in ["yes", "true", "1"]
        try:
            m2_slots = int(mb.get("m2_slots", 0))
        except (ValueError, TypeError):
            m2_slots = 0
        return nvme_flag or m2_slots > 0
    if iface == "SATA":
        try:
            return int(mb.get("sata_ports", 0)) > 0
        except (ValueError, TypeError):
            return False
    return False


def psu_sufficient(psu, cpu, gpu):
    try:
        cpu_tdp = float(cpu.get("tdp_watts", 0))
        gpu_tdp = float(gpu.get("tdp_watts", 0)) if gpu else 0.0
        required = cpu_tdp + gpu_tdp + 20
        psu_wattage = float(psu.get("wattage", 0))
        return psu_wattage >= required
    except (ValueError, TypeError):
        return False


def within_budget(total_price, budget):
    try:
        return float(total_price) <= float(budget)
    except (ValueError, TypeError):
        return False


def apply_purpose_pruning(component_type, component, purpose):
    purpose = normalize_purpose_name(purpose)

    if purpose == "Gaming":
        # Gaming is performance-oriented: prune weak components early.
        if component_type == "gpu" and float(component.get("vram_gb", 0)) < 10:
            return False
        if component_type == "cpu" and int(component.get("cores", 0)) < 8:
            return False
        if component_type == "ram" and float(component.get("capacity_gb", 0)) < 16:
            return False

    elif purpose == "Office":
        if component_type == "gpu" and float(component.get("price_usd", 0)) > 400:
            return False

    elif purpose == "Content Creation":
        if component_type == "cpu" and int(component.get("cores", 0)) < 8:
            return False
        if component_type == "ram" and float(component.get("capacity_gb", 0)) < 32:
            return False
        if component_type == "storage" and str(component.get("interface", "")).strip().upper() != "NVME":
            return False

    elif purpose == "AI Workstation":
        if component_type == "gpu" and float(component.get("vram_gb", 0)) < 16:
            return False
        if component_type == "psu" and float(component.get("wattage", 0)) < 750:
            return False
        if component_type == "cpu" and int(component.get("cores", 0)) < 8:
            return False

    elif purpose == "Budget Build":
        if component_type == "cpu" and float(component.get("price_usd", 0)) > 250:
            return False
        if component_type == "gpu" and float(component.get("price_usd", 0)) > 300:
            return False
        if component_type == "ram" and float(component.get("price_usd", 0)) > 100:
            return False
        if component_type == "mb" and float(component.get("price_usd", 0)) > 150:
            return False
        if component_type == "storage" and float(component.get("price_usd", 0)) > 100:
            return False
        if component_type == "psu" and float(component.get("price_usd", 0)) > 100:
            return False

    elif purpose == "High-End Build":
        if component_type == "gpu" and float(component.get("vram_gb", 0)) < 12:
            return False
        if component_type == "cpu" and int(component.get("cores", 0)) < 8:
            return False
        if component_type == "ram" and float(component.get("capacity_gb", 0)) < 32:
            return False
        if component_type == "psu" and float(component.get("wattage", 0)) < 750:
            return False

    return True

if __name__ == "__main__":
    cpu  = {"name": "Ryzen 5 5600X", "socket": "AM4", "tdp_watts": 65, "cores": 6}
    mb   = {"name": "ASUS B550M-A", "socket": "AM4", "ram_type": "DDR4", "nvme_support": "Yes", "sata_ports": 6}
    ram  = {"name": "Corsair 16GB", "type": "DDR4", "capacity_gb": 16}
    stor = {"name": "Samsung 970", "interface": "NVMe"}
    gpu  = {"name": "RTX 3060", "vram_gb": 12, "tdp_watts": 170, "price_usd": 330}
    psu  = {"name": "Corsair RM650x", "wattage": 650}

    total_price = 848.0

    print("=== اختبار قواعد التوافق ===\n")
    print(f"CPU  <-> Motherboard: {cpu_mb_compatible(cpu, mb)}")
    print(f"RAM  <-> Motherboard: {ram_mb_compatible(ram, mb)}")
    print(f"Storage  <-> Motherboard: {storage_mb_compatible(stor, mb)}")
    print(f"PSU sufficient: {psu_sufficient(psu, cpu, gpu)}")
    print(f"Total price: {total_price}")
    print(f"Within budget 1000: {within_budget(total_price, 1000)}")

    all_compatible = (
        cpu_mb_compatible(cpu, mb) and
        ram_mb_compatible(ram, mb) and
        storage_mb_compatible(stor, mb) and
        psu_sufficient(psu, cpu, gpu)
    )
    print(f"Build complete: True")
    print(f"Build valid: {all_compatible}")

    print("\n=== اختبار Purpose Pruning ===\n")
    print(f"Gaming  - GPU vram=4  : {apply_purpose_pruning('gpu', {'vram_gb': 4, 'price_usd': 200}, 'Gaming')}")
    print(f"Gaming  - GPU vram=12 : {apply_purpose_pruning('gpu', {'vram_gb': 12, 'price_usd': 330}, 'Gaming')}")
    print(f"Office  - GPU price=500 : {apply_purpose_pruning('gpu', {'vram_gb': 8, 'price_usd': 500}, 'Office')}")
    print(f"AI Workstation - GPU vram=8 : {apply_purpose_pruning('gpu', {'vram_gb': 8, 'price_usd': 400}, 'AI Workstation')}")