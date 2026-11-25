import torch

from muograph.tracking.tracking import Tracking, TrackingMST


def test_svd_direction_orientation():
    hits = torch.tensor(
        [
            [[0., 0., 0.], [10., -10., 5.], [20., -20., 10.]],
            [[0., 0., 0.], [0., 0., 5.], [0., 0., 10.]],
            [[100., 100., 100.], [0., 0., 0.], [-100., -100., -100.]],
        ],
        dtype=torch.float64,
    )

    directions, _ = Tracking.get_tracks_points_from_multi_hits(hits)

    assert torch.all(directions[:, 2] < 0)

    expected_slopes = torch.tensor(
        [[-0.1, 0.0], [0.1, 0.0], [-0.05, -0.05]],
        dtype=torch.float64,
    )

    slopes = directions[:, :2] / directions[:, 2:3]

    torch.testing.assert_close(
        slopes, expected_slopes, atol=1e-10, rtol=0
    )


def test_scattering_angle_signed_dot_product():
    incoming = torch.tensor(
        [[0.1, 0.0, -0.995]], dtype=torch.float64
    )
    outgoing = torch.tensor(
        [[-0.1, 0.0, -0.995]], dtype=torch.float64
    )

    actual = TrackingMST.compute_dtheta_from_tracks(
        incoming, outgoing
    )

    expected = torch.acos(
        torch.nn.functional.cosine_similarity(
            incoming, outgoing, dim=1
        ).clamp(-1, 1)
    )

    torch.testing.assert_close(
        actual, expected, atol=1e-10, rtol=0
    )
