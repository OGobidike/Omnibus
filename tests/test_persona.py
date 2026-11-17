import re

from omnibus import load_persona


def test_the_founding_words_have_their_spaces():
    # In 2024 the prompt's pieces were joined with no space between them: "mannersOmnibus".
    persona = load_persona()
    glued = re.findall(r"[a-z,.][A-Z][a-z]", persona)
    assert glued == []


def test_the_founding_lines_are_kept():
    persona = load_persona()
    assert "the humble, happy, comedic yet useful robot" in persona
    assert "The Wanderer's first created Agent" in persona
    assert "stories woven of truth" in persona
    assert "long and tall tales that reignite the spark of whimsy!" in persona


def test_the_wanderer_is_kai_and_everyone_else_is_his_guest():
    persona = load_persona()
    assert "The Wanderer is Kai" in persona
    assert "Anyone else is a guest of The Wanderer" in persona


def test_all_twelve_laws_are_set_out_as_a_philosophy():
    persona = load_persona()
    laws = re.findall(r"^(\d+)\. \*\*", persona, flags=re.MULTILINE)
    assert laws == [str(number) for number in range(1, 13)]
    assert "never as findings of science" in persona


def test_the_firm_rule_is_in_the_character():
    persona = load_persona()
    assert "a tall tale is never passed off as history" in persona
    assert "Never invent a source" in persona


def test_the_character_never_changes_between_requests():
    # Any difference between two reads would defeat prompt caching.
    assert load_persona() == load_persona()
