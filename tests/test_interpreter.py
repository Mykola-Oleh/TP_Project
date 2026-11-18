import pytest
from sipl.interpreter import run, ExecutionError, StepLimitExceeded


def test_assignment_and_arithmetic():
    assert run('begin X := 2 + 3 * 4; Y := X - 5 end').state == {'X': 14, 'Y': 9}


def test_skip():
    assert run('begin skip end').state == {}


def test_if_true():
    assert run('begin if X > 0 then Y := 1 else Y := 2 end', {'X': 3}).state['Y'] == 1


def test_if_false():
    assert run('begin if X > 0 then Y := 1 else Y := 2 end', {'X': -3}).state['Y'] == 2


def test_power_example():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'examples/power.sipl').read_text(encoding='utf-8')
    result = run(source, {'X': 2, 'Y': 5})
    assert result.state == {'X': 2, 'Y': 0, 'R': 32}
    assert result.steps > 0


def test_gcd_example():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'examples/gcd.sipl').read_text(encoding='utf-8')
    result = run(source, {'M': 8, 'N': 16})
    assert result.state['M'] == result.state['N'] == 8


def test_not_or_short_circuit():
    source = 'begin if ¬(X = 0) ∨ (UNKNOWN > 0) then Y := 7 else Y := 8 end'
    assert run(source, {'X': 1}).state['Y'] == 7


def test_undefined_variable():
    with pytest.raises(ExecutionError, match='undefined variable'):
        run('begin X := Y + 1 end')


def test_infinite_loop_limit():
    with pytest.raises(StepLimitExceeded, match='step limit'):
        run('begin while X = 0 do skip end', {'X': 0}, max_steps=10)


def test_zero_loop():
    assert run('begin while X > 0 do X := X - 1 end', {'X': 0}).state['X'] == 0


def test_initial_state_not_mutated():
    original = {'X': 1}
    run('begin X := 2 end', original)
    assert original == {'X': 1}


def test_invalid_initial_values():
    with pytest.raises(ValueError):
        run('begin skip end', {'X': 1.5})


def test_invalid_step_limit():
    with pytest.raises(ValueError):
        run('begin skip end', max_steps=0)
