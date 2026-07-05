from src.evaluator import evaluate_echo, grade_for_score
from src.models import BuildRule, EchoItem, SubStat


def test_grade_thresholds():
    assert grade_for_score(85) == "excellent"
    assert grade_for_score(70) == "keep"
    assert grade_for_score(50) == "upgrade"
    assert grade_for_score(30) == "hold"
    assert grade_for_score(10) == "replace"
    assert grade_for_score(0) == "discard"


def test_evaluate_echo_scores_matching_stats():
    rule = BuildRule(
        character_name="default_main_dps",
        role="main_dps",
        recommended_sets=["Molten Rift"],
        priority_stats=["Crit Rate", "Crit DMG", "ATK%"],
        useful_sub_stats=["Crit Rate", "Crit DMG", "ATK%"],
        bad_sub_stats=["DEF"],
    )
    echo = EchoItem(
        name="Good Echo",
        set_name="Molten Rift",
        level=25,
        main_stat="Crit Rate",
        sub_stats=[SubStat(name="Crit DMG", value="16%"), SubStat(name="ATK%", value="8%")],
    )
    diagnosis = evaluate_echo(echo, rule)
    assert diagnosis.target_type == "echo"
    assert diagnosis.score >= 75
    assert diagnosis.grade in ["keep", "excellent"]
