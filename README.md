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

## Етап 4 — CORE-05: стабільний CLI (1 бал)

CLI підтримує `check`, `parse`, `run`, `trace`, а також `--json`, `--var NAME=INTEGER`
(можна повторювати) та `--max-steps N`.

### Контракт JSON v1.0

При `--json` stdout завжди містить **один JSON-об'єкт** із полями:

```json
{
  "schema_version": "1.0",
  "command": "check",
  "ok": true,
  "data": {"valid": true},
  "error": null
}
```

- `schema_version`: рядок `"1.0"`.
- `command`: одна з `check`, `parse`, `run`, `trace`.
- `ok`: логічний результат.
- `data`: об'єкт або `null` при помилці. Для `parse` містить `ast`;
  для `run` — `state`, `steps`; для `trace` — `result`, `events`.
- `error`: `null` при успіху або об'єкт `{type, message, location}`.
  `location` може бути `null`, `{line, column}` для синтаксичної помилки
  або `{line, column, end_line, end_column}` для помилки виконання.

У звичайному режимі `check` друкує `Syntax OK`, а інші команди зберігають
попередній формат виводу. Помилки без `--json` надходять до stderr.

### Коди завершення

| Код | Значення |
| --- | --- |
| `0` | Успіх |
| `2` | Помилка аргументів або вхідного файлу |
| `3` | Синтаксична помилка SIPL |
| `4` | Помилка виконання SIPL або перевищення ліміту кроків |

Для некоректних аргументів самого `argparse` застосовується стандартний код `2`
та повідомлення у stderr, навіть якщо передано `--json`.

### Інтеграційні тести

`tests/test_cli.py` запускає CLI у дочірньому процесі, перевіряє stdout,
JSON-поля, коди завершення та повідомлення про помилки.

**Обмеження контракту:** JSON v1.0 фіксує структуру відповіді CLI; формат
внутрішнього AST та подій trace може бути уточнений у наступних версіях.


## Етап 5 — CORE-06 + VIS-01 (2.5 бала)

### Незалежний conformance suite (CORE-06)

Файли `conformance/*.json` — тестові випадки з **вхідною SIPL-програмою**, початковим станом,
режимом (`run`, `ast`, `error`) та заздалегідь заданими очікуваннями.
Сценарій `conformance/run_suite.py` викликає лише публічний CLI через окремий процес;
він не імпортує реалізацію парсера або інтерпретатора. Його можна запускати
проти іншої реалізації, якщо вона підтримує CLI `parse`/`run` і JSON-протокол версії 1.0.

```powershell
py conformance/run_suite.py
py conformance/run_suite.py --command sipl
```

У режимі `run` порівнюються `state` і `steps`; у `error` — код завершення й тип помилки;
у `ast` — структурна форма AST. Усі тести незалежні.

### Дерево синтаксичного виводу (VIS-01)

Команда `visualize` будує **конкретне дерево розбору Lark** (не AST) і експортує
його в Text, JSON, DOT та SVG. Кожен вузол має `line`, `column`, `end_line`,
`end_column` для зв'язку з фрагментом джерела.

Особливості:
- Відображення терміналів і нетерміналів.
- Червона нумерація термінальних символів.
- Чорні стрілки між вузлами дерева.
- Послідовність терміналів під деревом.
- Відображення вихідного коду SIPL праворуч.
- Генерація SVG без встановлення Graphviz.

Для створення дерева:
```powershell
py -m sipl.cli visualize examples/gcd.sipl --format derivation-svg --output derivation.svg
```

Для експорту у DOT:
```powershell
py -m sipl.cli visualize examples/gcd.sipl --format derivation-dot --output derivation.dot
```

Звичайні формати `text`, `json`, `dot`, `svg` також залишаються доступними.


