import psutil

from lsh.utils.schema import CPUInfo, GPUInfo, MemoryInfo

try:
    import pynvml
    HAS_NVML = True
except ImportError:
    HAS_NVML = False


def measure_cpu() -> CPUInfo:
    usage_percent = psutil.cpu_percent(interval=1)
    cores_count = psutil.cpu_count(logical=True)
    return CPUInfo(usage_percent=usage_percent, cores_count=cores_count)


def measure_memory() -> MemoryInfo:
    memory = psutil.virtual_memory()
    return MemoryInfo(
        total_mb=memory.total / (1024 * 1024),
        used_mb=memory.used / (1024 * 1024),
        free_mb=memory.free / (1024 * 1024),
        usage_percent=memory.percent,
    )


def measure_gpu() -> list[GPUInfo]:
    if not HAS_NVML:
        return []
    gpus = []
    try:
        pynvml.nvmlInit()
        gpu_count = pynvml.nvmlDeviceGetCount()

        for i in range(gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_info = GPUInfo(
                id=i,
                model=pynvml.nvmlDeviceGetName(handle).decode() if isinstance(pynvml.nvmlDeviceGetName(handle), bytes) else pynvml.nvmlDeviceGetName(handle),
                temperature_c=pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                power_draw_w=pynvml.nvmlDeviceGetPowerUsage(handle) / 1000,
                memory_total_mb=mem_info.total / (1024 * 1024),
                memory_used_mb=mem_info.used / (1024 * 1024),
                memory_free_mb=mem_info.free / (1024 * 1024),
            )
            gpus.append(gpu_info)
    except Exception:
        pass
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
    return gpus
