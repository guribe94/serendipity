from tetris.scoring import (
    HARD_DROP_POINTS,
    LINES_PER_LEVEL,
    LINE_SCORES,
    SOFT_DROP_POINTS,
    Scoring,
)


def test_initial_state():
    s = Scoring()
    assert s.score == 0
    assert s.lines == 0
    assert s.level == 1


def test_starting_level_clamped_to_one():
    s = Scoring(starting_level=0)
    assert s.level == 1


def test_single_line_clear_awards_guideline_score():
    s = Scoring()
    s.add_line_clear(1)
    assert s.score == LINE_SCORES[1]


def test_tetris_awards_eight_hundred_at_level_one():
    s = Scoring()
    s.add_line_clear(4)
    assert s.score == LINE_SCORES[4]


def test_back_to_back_tetris_applies_one_and_a_half_multiplier():
    s = Scoring()
    s.add_line_clear(4)
    s.add_line_clear(4)
    # 800 + (800 * 1.5) + 50 (combo on second clear)
    assert s.score == LINE_SCORES[4] + (LINE_SCORES[4] * 3) // 2 + 50


def test_non_difficult_clear_resets_back_to_back_chain():
    s = Scoring()
    s.add_line_clear(4)  # 800, last difficult
    s.add_line_clear(1)  # 100 + 50 combo, last NOT difficult
    s.add_line_clear(4)  # 800 + 100 combo, NO b2b
    assert s.score == 800 + 150 + 900


def test_combo_counter_advances_and_resets():
    s = Scoring()
    s.add_line_clear(1)  # combo 0 -> no bonus, +100
    s.add_line_clear(1)  # combo 1 -> +50, +100 = 150
    s.add_line_clear(0)  # combo resets
    s.add_line_clear(1)  # combo 0 again, +100
    assert s.score == 100 + 150 + 0 + 100


def test_lines_accumulate_and_drive_level_up():
    s = Scoring()
    # 10 single clears = 10 lines = level 2.
    for _ in range(LINES_PER_LEVEL):
        s.add_line_clear(1)
    assert s.lines == LINES_PER_LEVEL
    assert s.level == 2


def test_soft_and_hard_drop_points():
    s = Scoring()
    s.add_soft_drop(5)
    s.add_hard_drop(10)
    assert s.score == SOFT_DROP_POINTS * 5 + HARD_DROP_POINTS * 10


def test_negative_drop_distances_do_not_subtract_score():
    s = Scoring()
    s.add_soft_drop(-3)
    s.add_hard_drop(-2)
    assert s.score == 0


def test_tspin_double_outscores_plain_double():
    s_plain = Scoring()
    s_plain.add_line_clear(2)
    s_tspin = Scoring()
    s_tspin.add_line_clear(2, tspin="full")
    assert s_tspin.score > s_plain.score


def test_level_only_advances_never_drops():
    s = Scoring(starting_level=5)
    s.add_line_clear(1)
    assert s.level == 5  # one line at level 5 should not regress to level 1


def test_initial_stats_all_zero():
    s = Scoring()
    assert s.stats == {
        "singles": 0,
        "doubles": 0,
        "triples": 0,
        "tetrises": 0,
        "tspins": 0,
        "tspin_minis": 0,
        "max_combo": 0,
    }


def test_clear_type_counters_track_line_counts():
    s = Scoring()
    s.add_line_clear(1)
    s.add_line_clear(2)
    s.add_line_clear(3)
    s.add_line_clear(4)
    assert s.stats["singles"] == 1
    assert s.stats["doubles"] == 1
    assert s.stats["triples"] == 1
    assert s.stats["tetrises"] == 1


def test_clear_type_counters_accumulate_per_line_count():
    s = Scoring()
    s.add_line_clear(1)
    s.add_line_clear(1)
    s.add_line_clear(2)
    assert s.stats["singles"] == 2
    assert s.stats["doubles"] == 1
    assert s.stats["triples"] == 0
    assert s.stats["tetrises"] == 0


def test_tspin_counters_track_full_and_mini():
    s = Scoring()
    s.add_line_clear(2, tspin="full")
    s.add_line_clear(1, tspin="mini")
    s.add_line_clear(0, tspin="full")  # full t-spin with no lines is still counted
    assert s.stats["tspins"] == 2
    assert s.stats["tspin_minis"] == 1


def test_tspin_clear_counts_toward_both_line_type_and_tspin():
    s = Scoring()
    s.add_line_clear(2, tspin="full")
    assert s.stats["doubles"] == 1
    assert s.stats["tspins"] == 1


def test_zero_line_lock_increments_no_clear_type_counter():
    s = Scoring()
    s.add_line_clear(0)
    assert s.stats["singles"] == 0
    assert s.stats["doubles"] == 0
    assert s.stats["triples"] == 0
    assert s.stats["tetrises"] == 0
    assert s.stats["tspins"] == 0
    assert s.stats["tspin_minis"] == 0


def test_max_combo_tracks_peak_and_survives_reset():
    s = Scoring()
    s.add_line_clear(1)  # combo 0
    s.add_line_clear(1)  # combo 1
    s.add_line_clear(1)  # combo 2 -> peak
    s.add_line_clear(0)  # combo resets to -1
    s.add_line_clear(1)  # combo 0 again
    assert s.stats["max_combo"] == 2


def test_stats_returns_fresh_dict_snapshot():
    s = Scoring()
    s.add_line_clear(4)
    snapshot = s.stats
    assert snapshot == {
        "singles": 0,
        "doubles": 0,
        "triples": 0,
        "tetrises": 1,
        "tspins": 0,
        "tspin_minis": 0,
        "max_combo": 0,
    }
    # Mutating the returned dict must not affect internal state.
    snapshot["tetrises"] = 999
    assert s.stats["tetrises"] == 1
