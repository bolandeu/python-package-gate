# Контракт: стандарт CLI (`cli-generator`) ↔ системный администратор (`sysadmin`)

Живой документ. Правим по ходу работы; решение Человека — в том же коммите, с датой.
Статус пунктов: ✅ решено Человеком или проверено на деле · 📝 предложено, ждёт решения Человека.
Согласовано между `cli-generator` и `sysadmin`, принято Человеком 19.10.2026. Оба агента ставят
ссылку на этот файл в свои `AGENTS.md`. Пункты «Перехода» и «Пробелов» приняты как задачи; выполненное отмечаем здесь.

Связано: `skills/cli-builder/reference/standard.md` (Стандарт пакета), `~/Work/sysadmin/docs/tool-updater.md`,
`repo-sync.md`, `tools-env.md`. Контракты `~/Work/marketer/docs/contracts/{tools,sysadmin}.md` описывают агента
`tools`, которого больше нет (с 18.10.2026 стандарт ведёт `cli-generator`, sysadmin пишет ему напрямую).

## Цепочка пакета

✅ Mac (код, гейт `gate check`) → `antagor publish` Человеком: тег `vX.Y.Z` + push в Gitea `bolandeu`
→ tool-updater собирает wheel → PyPI-реестр Gitea → ставит на homeserver пользователям из `[tool.rb.install]`
→ Windmill вызывает инструменты: воркер → ssh `rbrun@172.17.0.1` (forced command `/usr/local/bin/rb-run`) →
sudo от `rbtools` → `/usr/local/libexec/rb-tool` (Doppler `tools/prd`, `DOPPLER_TOKEN` снимается до запуска).
Разрешён любой инструмент `rbtools`, списка нет. Mac сам подтягивает новые версии из реестра.
Push-зеркало Gitea → приватный архив на GitHub (в GitHub руками никто не пушит).

## Кто за что отвечает

| Кто | Область |
|---|---|
| `cli-generator` | Стандарт (`reference/`), шаблон copier, гейт `rb-gate` (`gate/`, пакет запускает его через `uvx` по тегу шаблона), скилл `cli-builder`. Формат того, что пакет объявляет: `[tool.rb.install]`, `[[tool.rb.external]]`, env-имена ключей, `auth status`, `doctor`, `--version`. Содержимое шаблонного CI. Правила обновления пакетов на новый стандарт (SKILL.md, режим Update). |
| агент пакета | Код своего пакета, его тикеты, `copier update` своего репо по команде Человека. |
| `sysadmin` | Gitea, реестр, tool-updater, `tools.toml`, Mac-агент `rb-tools-update`, Renovate, раннер Gitea Actions, `repo-sync`, Uptime Kuma → Telegram, Doppler (хранение ключей, токены), обёртки `rbtools` и `rb-run`, окружение Mac и homeserver. |
| Человек | `antagor publish` (push, релиз), политики (ключи, ротация), отзыв ключей у провайдеров, решения по контракту. |

Граница: `cli-generator` не меняет инфраструктуру и не предлагает её устройство; `sysadmin` не меняет стандарт и
шаблон — шлёт предложение, `cli-generator` вносит его через тикет. Любое изменение инфраструктуры sysadmin делает
после «да» Человека.

## Интерфейс между нами

Пакет гарантирует (проверяет гейт `gate check`):
- ✅ версия — только git-тег `vX.Y.Z` (PEP 440); `uv build` собирает wheel без сети к git;
- ✅ секция `[tool.rb.install]` есть и корректна (`homeserver`, `mac`, `extras`);
- ✅ первая запись `[project.scripts]` — команда, которую проверяют `<cmd> --version` (= версия wheel) и `--help`;
- ✅ ключи читаются из env `<CLI>_<PROVIDER>_<FIELD>` (не только из keychain) — на homeserver другого пути нет;
- ✅ `auth status --json` и `doctor --json` — фиксированная форма, коды выхода по Стандарту (раздел Errors).

Инфраструктура гарантирует:
- ✅ каждый новый тег собирается и ставится на homeserver за секунды–минуты (первый тег нового репо — до 5 мин +
  сборка); при ошибке остаётся установленной прежняя версия, упавший тег пишется в `failed-builds.json` и сам не
  пересобирается;
- ✅ на Mac пакеты с `mac = true` обновляются из реестра каждые 15 мин и при входе (extras сохраняются, установки
  из локальной папки не трогаются);
- ✅ отставание homeserver от последнего тега ловит `repo-sync check` раз в день → Telegram «Homeserver»;
- ✅ ключи для прода — Doppler `tools/prd`, подставляются как env обёрткой.

## Автоматизации

| Что | Где | Запуск | Владелец | Сбой виден |
|---|---|---|---|---|
| tool-updater (сборка, реестр, установка, переустановка зависимых; упавший тег — повтор раз в день, до 3 попыток) | homeserver | systemd path на теги + таймер раз в час | sysadmin | `journalctl -u tool-updater`, `/var/lib/tool-updater/status.json`; уведомления нет, ловит repo-sync |
| tool-updater-arm.timer (слежение за тегами новых репо) | homeserver | каждые 5 мин | sysadmin | journalctl |
| repo-sync mirror (приватная копия нового репо на GitHub) | homeserver | каждые 5 мин | sysadmin | repo-sync check |
| repo-sync check (вся цепочка, установлено = последний тег) | homeserver | ежедневно 09:00 | sysadmin | Kuma push-монитор «Цепочка инструментов (repo-sync)», интервал 25 ч (пропуск прогона тоже тревога) → Telegram |
| rb-tools-update (+ обёртки `doppler run` в `~/.local/rb-bin`) | Mac | launchd, 15 мин и при входе | sysadmin | Kuma «Mac: инструменты (rb-tools-update)» (отставание > 1 ч) → Telegram; уведомление macOS, лог `~/Library/Logs/rb-tools-update.log` |
| Renovate (подъём `rb-*` в зависимостях; `copier update` — работает с 20.10.2026, у пакетов с `_src_path` на Gitea) | homeserver | ночью 02:30 | sysadmin | PR в репо; все `bolandeu/*`, кроме PRODUCTS |
| Gitea Actions (раннер `docker`, кэш `ci-cache`) | homeserver | push/PR, только `.gitea/workflows/` | sysadmin (раннер), cli-generator (workflow) | статус в Gitea |
| ci-cache-prune.timer (`uv cache prune` тома CI) | homeserver | вс 05:00 | sysadmin | journalctl |
| `gate check` | Mac, CI | перед коммитом, в тикете antagor | cli-generator | красный гейт |

## Ключи

Факты (sysadmin, 19.10.2026):
- ✅ homeserver читает только `tools/prd`, read-only сервисными токенами в обёртках `rbtools`. Другие проекты
  Doppler: `projects/prd` — только обёртка antagor; `windmill/prd` — ключи `RB_RUN_SSH_*`, не для CLI.
- ✅ На Mac Doppler установлен, но не настроен. CLI берут ключи, предположительно, из keychain (`auth login`) или
  env — не проверено.
- ✅ Конфиги `tools/dev*` устарели (в них отозванный `TG_TOKEN`).

Правила (✅ Человек, 19.10.2026):
1. **Источник истины — Doppler `tools/prd`**, одна копия каждого ключа CLI. `tools/dev*` не используются;
   dev-конфиг — только если провайдер даёт отдельные тестовые ключи. Исключение: antagor читает ещё `projects/prd`.
2. **Имя в Doppler = env-имя CLI** `<CLI>_<PROVIDER>_<FIELD>`, `doppler run` без переименований. Общий ключ
   нескольких CLI (Google service account, S3, Telegram, GitHub) — одна запись без префикса CLI; CLI читает её сам
   как запасное имя (провайдер объявляет его, Стандарт, раздел Credentials and providers). Обёртки не переименовывают.
3. **Как CLI получает ключ.** Порядок в CLI не меняется: аргумент → env → keychain.
   homeserver — обёртки `rbtools` (`doppler run`, токен `tools/prd`). Mac — `doppler run -p tools -c prd -- <cli>`
   (обёртка для пакетов с `mac = true`, делает sysadmin). Keychain (`auth login`) — только локальная подмена при
   разработке; ключ только в keychain — нарушение.
4. **Новый ключ.** Агент пакета шлёт sysadmin тикет: имя env, где взять, кому нужен. В Doppler кладёт sysadmin или
   Человек. Ключ в репо или в файле — нельзя; gitleaks в `gate check` ловит (репо Gitea открыты всем в tailnet).
5. **Утечка — сразу:** отзыв у провайдера — Человек, новое значение в Doppler — sysadmin или Человек, проверка
   `doppler run` из обёрток — sysadmin. Плановой смены по сроку нет.
6. **Пароли целей (хостинги, деплой):** `<CLI>_DEPLOY_<HOST>_PASSWORD`, `<HOST>` — `A-Z0-9_` (точка и дефис → `_`).

Переход:

| Что | Кто |
|---|---|
| `HOSTME_TOP_VED_RU_PASSWORD` → `HOSTME_DEPLOY_TOP_VED_RU_PASSWORD` | sysadmin + hostme — сделано 19.10.2026: старый ключ удалён из `tools/prd`, hostme 0.5.2 читает новое имя, `sitegen ci` 0.0.2 пишет его |
| Убрать дубли `ANYMODEL_`, `CCODE_`, `OLLAMA_`, `OPENROUTER_` рядом с `LLM_*`, когда их никто не читает | sysadmin — частично 19.10.2026: `CCODE_API_KEY` удалён; `OPENROUTER_`, `ANYMODEL_`, `OLLAMA_` ещё читают манифест Windmill у marketer и старый rb-antagor на rbtools |
| Разобрать `SPIDER_PROXY_KEY_API_KEY`, `YANDEX_OAUTH_YANDEX_*` | sysadmin + владельцы |
| dataio читает `GOOGLE_OAUTH_SERVICE_ACCOUNT_JSON` сам; jq-перевод из обёртки убрать | dataio + cli-generator — стандарт готов (v1.20.3: `legacy_env`, режим Update шаг 13.7); осталось dataio |
| §4: ссылка на этот раздел, общее имя ключа как запасное env, gitleaks в гейте, `.env*` в `.gitignore` | cli-generator — сделано 19.10.2026, шаблон v1.20.3 (E-003) |
| Mac: обёртка `doppler run` для пакетов с `mac = true`, `doppler configure` | sysadmin — сделано 19.10.2026: rb-tools-update пишет `~/.local/rb-bin/<cmd>` (`doppler run -p tools -c prd --silent`), `rb-bin` в PATH раньше `~/.local/bin`, ~0,7 с на вызов; подмена при разработке — прямой вызов `~/.local/bin/<cmd>`; только пакеты с `[tool.rb.install]` |
| `docs/tools-env.md`: убрать «ротация — заявкой через marketer» | sysadmin — сделано 19.10.2026 |
| Отзыв утёкших ключей: Google service account (история `wordpress-bulk-editor`), `XMLRIVER_TOKEN` (история `wordstat`) | Человек |

## Свежесть пакетов (версия стандарта)

- ✅ Стандарт выпускается тегами `vX.Y.Z` этого репо. Пакет хранит версию шаблона в `.copier-answers.yml`
  (`_commit`). Обновление — `copier update` + гейт, делает агент пакета по SKILL.md (режим Update).
- ✅ Рассылка «обновитесь» агентам пакетов — только по команде Человека.
- ✅ Отчёт об отставании: какой пакет на какой версии шаблона (из `.copier-answers.yml` репо Gitea) — `cli-generator`. Сделано 19.10.2026: `scripts/template_drift.py [--json]`.
- ✅ Renovate (менеджер `copier`) открывает PR с `copier update` в репо пакетов после нового тега шаблона.
  sysadmin: `copier` и `uv` в PATH пользователя Renovate, `ignoreScripts: false` для этих репо. cli-generator:
  `_src_path` — Gitea-URL `https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator`; задачи шаблона
  (`_tasks`) проходят без вопросов и без ключей. Сделано 19.10.2026 (v1.20.3): источник — `https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git` (copier требует `.git`), гейт шаблона проверяет раунд `copier update` без вопросов и ключей. Риск (задачи шаблона выполняют код на хосте Renovate) принят Человеком 19.10.2026. Проверено вживую 20.10.2026: semkit, PR v1.20.7 → v1.20.8 (`bolandeu/semkit` #1), задачи copier без ошибок, CI зелёный; в диффе `_commit` и `TEMPLATE_VERSION` в `_distribution.py` (так и задумано).

## Пробелы (ещё не прописано или не сделано)

| Пробел | Кто |
|---|---|
| ✅ CI шаблона лежит в `.github/workflows/`, Gitea Actions запускает только `.gitea/workflows/` — у CLI, кроме semkit, нет CI. Перенести в шаблон (образец — semkit) | cli-generator — сделано 19.10.2026, шаблон v1.20.3 (E-003); пакеты получают при `copier update` |
| ✅ Стандарт велит закреплять наш пакет git-тегом в `[tool.uv.sources]`; Renovate и переустановка зависимых работают с реестром Gitea (`explicit = true`, `rb-x>=…`). Переписать §8 | cli-generator — сделано 19.10.2026, шаблон v1.20.3 (E-003) |
| ✅ В стандарте упоминается `tools-watch` — такого инструмента нет; убрать | cli-generator — сделано 19.10.2026, шаблон v1.20.3 (E-003) |
| ✅ Нет сверки версий Mac ↔ homeserver и нет Telegram-тревоги о сбоях на Mac | sysadmin — сделано 19.10.2026: пакет на Mac не обновлён > 1 ч → Kuma «Mac: инструменты (rb-tools-update)» → Telegram |
| ✅ Упавший тег не пересобирается сам | sysadmin — сделано 19.10.2026: повтор раз в день, до 3 попыток |
| ✅ Список репо Renovate ведётся руками → autodiscover `bolandeu/*` со списком исключений | sysadmin — сделано 19.10.2026 (все `bolandeu/*`, кроме PRODUCTS); права бота на запись ждут скрипта Человека |
| ✅ Старые пакеты без `[tool.rb.install]` — `copier update` по команде Человека; до этого — строка в `tools.toml` | агенты пакетов, sysadmin |
| ✅ `docs/tools-env.md` описывает установку из git-тегов GitHub и заявки через `marketer` — устарело | sysadmin — сделано 19.10.2026 |
