import pytest
from sipl.trace import trace
from sipl.interpreter import ExecutionError, StepLimitExceeded, Interpreter
from sipl.parser import parse

def test_assignment_event_order():
    t = trace("begin X := 3 end")
    assert [e["event"] for e in t.events] == [
        "BeforeStatement", "VariableChanged", "AfterStatement", "ExecutionFinished"]
    assert t.events[1]["old_value"] is None
    assert t.events[1]["new_value"] == 3
    assert t.events[1]["state"] == {"X": 3}
    assert t.events[-1]["status"] == "success"

def test_condition_and_loop():
    source = "begin while X > 0 do X := X - 1 end"
    t = trace(source, {"X": 2})
    assert [e["value"] for e in t.events if e["event"] == "ConditionEvaluated"] == [True, True, False]
    assert t.result.state == {"X": 0}
    assert t.result.steps == 5

def test_if_condition():
    t = trace("begin if X > 0 then Y := 1 else Y := 2 end", {"X": 0})
    assert [e["value"] for e in t.events if e["event"] == "ConditionEvaluated"] == [False]
    assert t.result.state["Y"] == 2

def test_unchanged_runtime_result():
    source = "begin R := 1; while Y > 0 do begin R := R * X; Y := Y - 1 end end"
    assert trace(source, {"X": 2, "Y": 5}).result == Interpreter({"X": 2, "Y": 5}).run(parse(source))

def test_event_snapshots_are_independent():
    t = trace("begin X := 1; X := 2 end")
    assert [e["state"]["X"] for e in t.events if e["event"] == "VariableChanged"] == [1, 2]

def test_error_event_emitted():
    events = []
    with pytest.raises(ExecutionError):
        Interpreter(on_event=events.append).run(parse("begin X := Y end"))
    assert events[-1]["event"] == "ExecutionFinished"
    assert events[-1]["status"] == "error"

def test_step_limit_event():
    events = []
    with pytest.raises(StepLimitExceeded):
        Interpreter({"X": 1}, max_steps=2, on_event=events.append).run(parse("begin while X > 0 do skip end"))
    assert events[-1]["status"] == "error"

def test_span():
    t = trace("begin\n X := 1\nend")
    assert t.events[0]["span"]["line"] == 2
