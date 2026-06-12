from tetris.scoring import (
    HARD_DROP_POINTS,
    LINES_PER_LEVEL,
    LINE_SCORES,
    SOFT_DROP_POINTS,
    TSPIN_MINI_SCORES,
    TSPIN_SCORES,
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


def test_tspin_full_without_lines_scores_400():
    s = Scoring()
    delta = s.add_line_clear(0, tspin="full")
    assert delta == TSPIN_SCORES[0]
    assert s.score == TSPIN_SCORES[0]
    assert s.lines == 0


def test_tspin_mini_single_scores_200():
    s = Scoring()
    s.add_line_clear(1, tspin="mini")
    assert s.score == TSPIN_MINI_SCORES[1]


def test_back_to_back_survives_a_zero_line_tspin():
    s = Scoring()
    s.add_line_clear(4)                # 800, difficult
    s.add_line_clear(0, tspin="full")  # 400; combo resets, chain untouched
    s.add_line_clear(4)                # back-to-back: 1200, combo back to 0
    assert s.score == 800 + 400 + 1200


def test_line_scores_scale_with_level():
    s = Scoring(starting_level=3)
    s.add_line_clear(2)
    assert s.score == LINE_SCORES[2] * 3


def test_combo_bonus_scales_with_level():
    s = Scoring(starting_level=2)
    first = s.add_line_clear(1)   # 100 * 2, combo 0 -> no bonus
    second = s.add_line_clear(1)  # 100 * 2 + 50 * 1 * 2 combo bonus
    assert (first, second) == (200, 300)


def test_returned_deltas_always_sum_to_the_score():
    s = Scoring()
    total = 0
    for lines, tspin in ((1, None), (4, None), (0, None), (2, "full"), (0, "mini")):
        total += s.add_line_clear(lines, tspin=tspin)
    total += s.add_soft_drop(3)
    total += s.add_hard_drop(4)
    assert s.score == total
