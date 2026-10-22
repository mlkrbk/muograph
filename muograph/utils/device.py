
import os
import torch


def select_device():
    requested = os.environ.get("MUOGRAPH_DEVICE", "auto").lower()

    if requested not in ("auto", "cpu", "cuda", "mps"):
        raise ValueError(
            "MUOGRAPH_DEVICE must be auto, cpu, cuda, or mps"
        )

    if requested == "cpu":
        return torch.device("cpu")

    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable")
        return torch.device("cuda")

    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS is unavailable")
        return torch.device("mps")

    # Automatic device selection
    if torch.cuda.is_available():
        return torch.device("cuda")

    # Use CPU until MPS operations are validated
    return torch.device("cpu")


DEVICE = select_device()
print(f"Muograph device: {DEVICE}")

