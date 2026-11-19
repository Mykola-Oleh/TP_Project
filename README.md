# SIPL Toolkit — етап 1

Модулі: **CORE-01 (0,5 бала)** і **CORE-02 (1,5 бала)**.

## Синтаксис
- Програма: `begin <оператор> end` (непорожня).
- Оператори: `:=`, `;`, `if ... then ... else ...`, `while ... do ...`, `begin ... end`, `skip`.
- Арифметика: цілі числа, змінні, `+`, `-`, `*`, дужки.
- Умови: `=`, `>`, `∨`, `¬`, дужки.
- Пріоритет: `*`, потім `+/-`, потім порівняння, `¬`, `∨`.
- Послідовність операторів має найнижчий пріоритет; для вкладеної послідовності використовуй `begin/end`.

## Структура
- `src/sipl/grammar.lark`: граматика.
- `src/sipl/ast.py`: власні типізовані AST-вузли з SourceSpan.
- `src/sipl/parser.py`: перетворення Lark-дерева на AST та синтаксичні помилки.
- `src/sipl/cli.py`: команди `check` і `parse`.
- `examples/`: три приклади.
- `tests/`: позитивні/негативні тести.


## Етап 2 — CORE-03: Інтерпретатор (2 бали)

Виконує присвоювання, послідовність, `if`, `while`, `begin/end`, `skip`,
арифметику та умови. Вхідний стан — цілочисельні змінні. Змінні, які не
визначено, викликають помилку з позицією в коді. Кожна перевірка умови
циклу враховується у ліміті кроків, щоб зупиняти нескінченні цикли.

`run` виводить JSON з `state` (кінцевий стан) і `steps` (число кроків).
Для Python API: `from sipl.interpreter import run`.


## Етап 3 — CORE-04: trace (1 бал)

Події `BeforeStatement`, `AfterStatement`, `VariableChanged`,
`ConditionEvaluated`, `ExecutionFinished` доступні через callback
`Interpreter(..., on_event=callback)` та API `sipl.trace.trace(source, state)`.
Події містять `event`, `step`, `statement`, `span`, `state` (копія стану),
а також додаткові поля. `VariableChanged` має `variable`, `old_value`,
`new_value`; `ConditionEvaluated` має `value`; `ExecutionFinished` має
`status` та, у випадку помилки, `error`.

Trace виводить JSON із `result` (`state`, `steps`) та масивом `events`.
При помилці виконання callback отримує `ExecutionFinished(status=error)`,
але CLI завершується з кодом 1 і виводить повідомлення про помилку,
не частковий trace. Ліміт кроків працює як у попередньому етапі.
