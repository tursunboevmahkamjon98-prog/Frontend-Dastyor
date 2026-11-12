"""Russian button labels and keyboards for the administrator bot."""

LABELS = {
    'menu': '🏠 Главное меню', 'pending': '🧾 Проверить чеки',
    'credit': '💰 Пополнить баланс', 'finduser': '🔎 Найти пользователя',
    'history': '📜 История пополнений', 'stats': '📊 Статистика',
    'finance': '📈 Отчёт', 'paycontrol': '💳 Реквизиты',
    'cards': '🏦 Карты', 'expenses': '💸 Расходы', 'audit': '🗂 Журнал действий',
    'admins': '👥 Администраторы', 'help': '❓ Помощь',
    'cancel': '❌ Отмена', 'skip': '⏭ Без комментария',
    'addadmin': '➕ Добавить администратора', 'deladmin': '➖ Снять права',
}
PERMISSIONS = {
    'credit': 'balance.manage', 'pending': 'payments.view',
    'finduser': 'payments.view', 'history': 'reports.view', 'stats': 'reports.view',
    'finance': 'reports.view', 'paycontrol': 'cards.manage', 'cards': 'cards.manage',
    'expenses': 'expenses.manage', 'audit': 'audit.view', 'admins': 'admins.manage',
    'addadmin': 'admins.manage', 'deladmin': 'admins.manage',
}
MENU_TEXT = (
    '🏠 Панель администратора Dastyor\n\n'
    '🧾 Чеки — проверить заявки и подтвердить поступления.\n'
    '💰 Пополнить — начислить баланс после проверки перевода.\n'
    '🔎 Найти — посмотреть пользователя и его баланс.\n'
    '📈 Отчёт — неделя, статистика и последние пополнения.\n'
    '💳 Реквизиты — данные для перевода.\n\n'
    '👥 Администраторы: команда /admins (только полный доступ).'
)
HELP_TEXT = (
    '❓ Как пользоваться ботом\n\n'
    '🧾 «Проверить чеки» — открыть заявки и принять решение.\n'
    '💰 «Пополнить баланс» — выбрать пользователя, сумму и подтвердить.\n'
    '📈 «Отчёт» — заявки, поступления и расходы за неделю, статистика и последние пополнения.\n'
    '💳 «Реквизиты» — посмотреть или изменить данные для перевода.\n\n'
    '🏠 «Главное меню» — вернуться к разделам.\n'
    '❌ «Отмена» — прервать незавершённое действие.\n\n'
    'Сначала проверьте поступление денег в банковском приложении.'
)
# The label says what each level may do, so nobody picks "Support" for an
# admin who is meant to handle money.
TIERS = {'super': '👑 Полный доступ', 'finance': '💳 Финансы (чеки и баланс)',
         'support': '🎧 Поддержка (без денег)', 'readonly': '👁 Только просмотр'}

def button(action, label=None):
    return {'text': label or LABELS[action], 'callback_data': 'ui:' + action}

def navigation():
    return {'inline_keyboard': [[button('cancel'), button('menu')]]}

def menu(tier):
    # Only the five sections admins use every day. The other sections
    # (history, stats, cards, expenses, audit, admins, help) still work as
    # commands, e.g. /admins - they are just not buttons any more.
    rows = [('pending', 'credit'), ('finduser', 'finance'), ('paycontrol',)]
    if tier == 'support':
        allowed = {'pending', 'finduser', 'help'}
    elif tier == 'readonly':
        allowed = {'pending', 'finduser', 'history', 'stats', 'finance', 'audit', 'help'}
    elif tier == 'finance':
        allowed = set(LABELS) - {'admins', 'addadmin', 'deladmin'}
    else:
        allowed = set(LABELS) if tier == 'super' else {'help'}
    return {'inline_keyboard': [buttons for row in rows
                               if (buttons := [button(a) for a in row if a in allowed])]}

def shortcuts(tier):
    rows = [[{'text': LABELS['menu']}, {'text': LABELS['cancel']}]]
    if tier in ('super', 'finance'):
        rows.insert(0, [{'text': LABELS['pending']}, {'text': LABELS['credit']}])
    return {'keyboard': rows, 'resize_keyboard': True, 'is_persistent': True,
            'input_field_placeholder': 'Выберите действие или введите ответ'}

def context(state):
    rows = []
    if state.topup_stage == 'amount':
        rows.extend([[button('amount:' + str(n), f'{n} сомони') for n in (5, 10, 20)],
                     [button('amount:' + str(n), f'{n} сомони') for n in (50, 100)]])
    if state.topup_stage == 'note':
        rows.append([button('skip')])
    rows.extend(navigation()['inline_keyboard'])
    return {'inline_keyboard': rows}

def review(request_id):
    return {'inline_keyboard': [
        [{'text': '✅ Подтвердить', 'callback_data': 'pay:ok:' + request_id},
         {'text': '❌ Отклонить', 'callback_data': 'pay:no:' + request_id}],
        [{'text': '💵 Другая сумма', 'callback_data': 'pay:amt:' + request_id}],
        [{'text': '🔎 Доп. проверка', 'callback_data': 'pay:more:' + request_id}],
        [button('menu')],
    ]}
