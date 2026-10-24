import torch
from muograph.hits.hits import Hits
from muograph.tracking.tracking import Tracking, TrackingMST
from muograph.reconstruction.poca import POCA, POCAParams
from muograph.volume.volume import Volume

import os

# Test data file path
TEST_HIT_FILE = os.path.dirname(__file__) + "/../data/iron_barrel/barrel_and_cubes_scattering.csv"
VOI = Volume(position=(0, 0, -1200), dimension=(1000, 600, 600), voxel_width=(20, 10, 20))


def get_mst(hits_file: str) -> TrackingMST:
    hits_in = Hits(
        plane_labels=(0, 1, 2),
        data=hits_file,
        spatial_res=(1.0, 1.0, 0.0),
        energy_range=(0.0, 1_000_000),
        efficiency=0.98,
        input_unit="mm",
    )

    hits_out = Hits(
        plane_labels=(3, 4, 5),
        data=hits_file,
        spatial_res=(1.0, 1.0, 0.0),
        energy_range=(0.0, 1_000_000),
        efficiency=0.98,
        input_unit="mm",
    )

    tracks_in = Tracking(label="above", hits=hits_in)
    tracks_out = Tracking(label="below", hits=hits_out)

    return TrackingMST(trackings=(tracks_in, tracks_out))


def test_poca_predictions() -> None:
    mst = get_mst(TEST_HIT_FILE)

    poca: POCA[POCAParams] = POCA(tracking=mst, voi=VOI)  # type: ignore

    n_poca_uranium_x_region = poca.n_poca_per_vox[23:28].float().mean()
    n_poca_empty_x_region = poca.n_poca_per_vox[-5:].float().mean()

    assert (
        n_poca_uranium_x_region > n_poca_empty_x_region
    ), "The average number of POCA points per voxel in the uranium x region {n_poca_uranium_x_region} must be higher than in the empty region {n_poca_empty_x_region}"

def test_parallel_mask_rotation_invariance() -> None:
    """Rotating the same nonparallel tracks must not change classification."""

    theta = torch.deg2rad(torch.tensor(1.0, dtype=torch.float64))

    tracks_in = torch.tensor(
        [[0.0, 0.0, 1.0]],
        dtype=torch.float64,
    )

    tracks_out = torch.stack(
        [
            torch.sin(theta),
            torch.zeros_like(theta),
            torch.cos(theta),
        ]
    ).reshape(1, 3)

    # A proper 3D rotation: 120 degrees around (1, 1, 1).
    rotation = torch.tensor(
        [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=torch.float64,
    )

    # Use a general orientation with nonzero cross-product components.
    axis = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float64)
    axis = axis / torch.linalg.vector_norm(axis)

    angle = torch.deg2rad(torch.tensor(47.0, dtype=torch.float64))
    x, y, z = axis
    K = torch.stack([
        torch.stack([torch.zeros_like(x), -z, y]),
        torch.stack([z, torch.zeros_like(x), -x]),
        torch.stack([-y, x, torch.zeros_like(x)]),
    ])

    R = (
        torch.eye(3, dtype=torch.float64)
        + torch.sin(angle) * K
        + (1.0 - torch.cos(angle)) * (K @ K)
    )

    rotated_in = tracks_in @ R.T
    rotated_out = tracks_out @ R.T

    original_mask = POCA.compute_parallel_mask(
        tracks_in, tracks_out
    )

    rotated_mask = POCA.compute_parallel_mask(
        rotated_in, rotated_out
    )

    assert original_mask.item() is True
    assert rotated_mask.item() is True

def test_parallel_mask_edge_cases() -> None:
    """Check parallel, near-parallel, and zero-length vectors."""

    tracks_in = torch.tensor(
        [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
    )

    tracks_out = torch.tensor(
        [
            [0.0, 0.0, 1.0],
            [1e-9, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=torch.float64,
    )

    mask = POCA.compute_parallel_mask(tracks_in, tracks_out)

    assert mask.tolist() == [False, False, False]

def test_parallel_mask_vector_scaling() -> None:
    """Scaling direction vectors must not change their classification."""

    for dtype in (torch.float32, torch.float64):
        tracks_in = torch.tensor(
            [[0.0, 0.0, 1.0]],
            dtype=dtype,
        )

        tracks_out = torch.tensor(
            [[0.01, 0.02, 1.0]],
            dtype=dtype,
        )

        original = POCA.compute_parallel_mask(
            tracks_in, tracks_out
        )

        scaled = POCA.compute_parallel_mask(
            tracks_in * 100.0,
            tracks_out * 0.01,
        )

        assert original.item() is True
        assert torch.equal(original, scaled)