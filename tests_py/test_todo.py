"""TodoMVC 端到端测试 —— tests/todo.spec.js 的 Python 重写。

项目知识：勾选框的 check() / uncheck() 与 click() 怎么选

默认用 check() / uncheck()：它除了点击，还会回读并断言元素最终处于勾选（或未勾选）
状态，语义更强，能顺带覆盖「状态是否真的切换成功」。

但当这次操作会导致元素从 DOM 中消失时，必须改用 click()。例如
「6. 过滤器 › Active 视图下勾选完成，该条从列表中消失」：勾选后该条立即被过滤掉、
脱离 DOM，而 check() 内部要等待的「元素已勾选」这个状态永远不会出现，于是会一直
重试到超时（而不是快速失败，报错信息也只会指向 check 本身，容易误导）。
这类场景的写法是：用 click() 触发操作，再用业务结果断言（条目数量、列表内容）验证。

判断标准：操作之后元素是否还在页面上。还在 → check()；会被移除 → click()。
"""

import re

from playwright.sync_api import Locator, Page, expect

TODO_ITEMS = ["buy some cheese", "feed the cat", "book a doctors appointment"]


# ---- 定位辅助 ----
def new_todo(page: Page) -> Locator:
    """新建 todo 的输入框。"""
    return page.locator(".new-todo")


def todo_items(page: Page) -> Locator:
    """列表里所有 todo 条目。"""
    return page.locator(".todo-list li")


def todo_titles(page: Page) -> Locator:
    """每条 todo 的标题文本。"""
    return page.locator(".todo-list li label")


def completed_items(page: Page) -> Locator:
    """已完成条目。"""
    return page.locator(".todo-list li.completed")


def toggle_all(page: Page) -> Locator:
    """左侧「全部完成」勾选框。"""
    return page.locator(".toggle-all")


def todo_count(page: Page) -> Locator:
    """剩余计数。"""
    return page.locator(".todo-count")


def main_section(page: Page) -> Locator:
    """主列表区，无数据时整个不渲染。"""
    return page.locator(".main")


def footer(page: Page) -> Locator:
    """底栏，无数据时整个不渲染。"""
    return page.locator(".footer")


def clear_completed(page: Page) -> Locator:
    """Clear completed 按钮。"""
    return page.get_by_role("button", name="Clear completed")


# ---- 操作辅助 ----
def add_todo(page: Page, text: str) -> None:
    new_todo(page).fill(text)
    new_todo(page).press("Enter")


def add_todos(page: Page, items: list[str]) -> None:
    for text in items:
        add_todo(page, text)


def start_editing(item: Locator, text: str | None = None) -> Locator:
    """双击条目进入编辑态，返回该条目的 .edit 输入框。"""
    item.locator("label").dblclick()
    edit_input = item.locator(".edit")
    expect(edit_input).to_be_visible()
    if text is not None:
        edit_input.fill(text)
    return edit_input


def toggle_item(item: Locator) -> None:
    """勾选某个条目。"""
    item.locator(".toggle").check()


class TestInitialState:
    """1. 初始状态"""

    def test_input_visible_with_placeholder_and_focused(self, todo_page: Page):
        expect(new_todo(todo_page)).to_be_visible()
        expect(new_todo(todo_page)).to_have_attribute(
            "placeholder", "What needs to be done?"
        )
        expect(new_todo(todo_page)).to_be_focused()

    def test_list_and_footer_hidden_when_empty(self, todo_page: Page):
        expect(todo_items(todo_page)).to_have_count(0)
        expect(main_section(todo_page)).to_be_hidden()
        expect(footer(todo_page)).to_be_hidden()

    def test_clear_completed_hidden_when_empty(self, todo_page: Page):
        expect(clear_completed(todo_page)).to_be_hidden()


class TestAddTodo:
    """2. 新增 todo"""

    def test_add_by_enter_shows_list_and_footer(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])

        expect(todo_items(todo_page)).to_have_count(1)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0]])
        expect(todo_count(todo_page)).to_have_text("1 item left")
        expect(main_section(todo_page)).to_be_visible()
        expect(footer(todo_page)).to_be_visible()

    def test_input_cleared_after_add(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])

        expect(new_todo(todo_page)).to_have_value("")

    def test_add_multiple_keeps_insertion_order(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)

        expect(todo_items(todo_page)).to_have_count(3)
        expect(todo_titles(todo_page)).to_have_text(TODO_ITEMS)
        expect(todo_count(todo_page)).to_have_text("3 items left")

    def test_surrounding_whitespace_is_trimmed(self, todo_page: Page):
        add_todo(todo_page, f"   {TODO_ITEMS[0]}   ")

        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0]])

    def test_blank_input_creates_no_item(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        add_todo(todo_page, "")
        add_todo(todo_page, "     ")

        expect(todo_items(todo_page)).to_have_count(1)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0]])


class TestToggleCompletion:
    """3. 完成状态切换"""

    def test_check_marks_completed_and_decrements_count(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        first = todo_items(todo_page).nth(0)

        toggle_item(first)

        expect(first).to_have_class(re.compile(r"completed"))
        expect(first.locator(".toggle")).to_be_checked()
        expect(completed_items(todo_page)).to_have_count(1)
        expect(todo_count(todo_page)).to_have_text("2 items left")

    def test_uncheck_restores_active_state(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        toggle_item(item)
        expect(item).to_have_class(re.compile(r"completed"))

        item.locator(".toggle").uncheck()

        expect(item).not_to_have_class(re.compile(r"completed"))
        expect(completed_items(todo_page)).to_have_count(0)
        expect(todo_count(todo_page)).to_have_text("1 item left")

    def test_count_text_singular_and_plural(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        expect(todo_count(todo_page)).to_have_text("1 item left")

        add_todo(todo_page, TODO_ITEMS[1])
        expect(todo_count(todo_page)).to_have_text("2 items left")

    def test_toggle_all_completes_and_clears_everything(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)

        toggle_all(todo_page).check()

        expect(completed_items(todo_page)).to_have_count(3)
        expect(todo_count(todo_page)).to_have_text("0 items left")

        toggle_all(todo_page).uncheck()

        expect(completed_items(todo_page)).to_have_count(0)
        expect(todo_count(todo_page)).to_have_text("3 items left")

    def test_toggle_all_reflects_individual_toggles(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        for i in range(len(TODO_ITEMS)):
            toggle_item(todo_items(todo_page).nth(i))
        expect(toggle_all(todo_page)).to_be_checked()

        todo_items(todo_page).nth(1).locator(".toggle").uncheck()

        expect(toggle_all(todo_page)).not_to_be_checked()
        expect(todo_count(todo_page)).to_have_text("1 item left")


class TestEditing:
    """4. 编辑"""

    def test_double_click_enters_edit_mode_with_current_text(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        edit_input = start_editing(item)

        expect(item).to_have_class(re.compile(r"editing"))
        expect(edit_input).to_have_value(TODO_ITEMS[0])

    def test_enter_saves_and_leaves_edit_mode(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        edit_input = start_editing(item, "buy some sausages")
        edit_input.press("Enter")

        expect(item).not_to_have_class(re.compile(r"editing"))
        expect(todo_titles(todo_page)).to_have_text(["buy some sausages"])
        expect(todo_count(todo_page)).to_have_text("1 item left")

    def test_blur_saves_changes(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        start_editing(item, "buy some sausages")
        todo_page.get_by_role("heading", name="todos").click()

        expect(item).not_to_have_class(re.compile(r"editing"))
        expect(todo_titles(todo_page)).to_have_text(["buy some sausages"])

    def test_escape_discards_changes(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        edit_input = start_editing(item, "buy some sausages")
        edit_input.press("Escape")
        # 不论 Esc 是否直接退出编辑态，最终落库的都应该是原文本
        todo_page.get_by_role("heading", name="todos").click()

        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0]])

    def test_saving_empty_text_deletes_item(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        item = todo_items(todo_page).nth(0)

        edit_input = start_editing(item, "")
        edit_input.press("Enter")

        expect(todo_items(todo_page)).to_have_count(2)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[1], TODO_ITEMS[2]])

    def test_editing_one_item_keeps_others_completion(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        second = todo_items(todo_page).nth(1)
        toggle_item(second)

        first = todo_items(todo_page).nth(0)
        edit_input = start_editing(first, "buy some sausages")
        edit_input.press("Enter")

        expect(todo_titles(todo_page)).to_have_text(
            ["buy some sausages", TODO_ITEMS[1], TODO_ITEMS[2]]
        )
        expect(second).to_have_class(re.compile(r"completed"))
        expect(second.locator(".toggle")).to_be_checked()
        expect(todo_count(todo_page)).to_have_text("2 items left")


class TestDelete:
    """5. 删除"""

    def test_hover_delete_button_removes_item(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        second = todo_items(todo_page).nth(1)

        second.hover()
        second.get_by_role("button", name="Delete").click()

        expect(todo_items(todo_page)).to_have_count(2)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0], TODO_ITEMS[2]])
        expect(todo_count(todo_page)).to_have_text("2 items left")

    def test_deleting_middle_item_keeps_remaining_order(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        first = todo_items(todo_page).nth(0)

        first.hover()
        first.get_by_role("button", name="Delete").click()

        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[1], TODO_ITEMS[2]])

    def test_deleting_last_item_hides_list_and_footer(self, todo_page: Page):
        add_todo(todo_page, TODO_ITEMS[0])
        item = todo_items(todo_page).nth(0)

        item.hover()
        item.get_by_role("button", name="Delete").click()

        expect(todo_items(todo_page)).to_have_count(0)
        expect(main_section(todo_page)).to_be_hidden()
        expect(footer(todo_page)).to_be_hidden()


class TestFilters:
    """6. 过滤器"""

    def test_filter_links_switch_and_highlight(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        all_link = todo_page.get_by_role("link", name="All")
        active_link = todo_page.get_by_role("link", name="Active")
        completed_link = todo_page.get_by_role("link", name="Completed")

        expect(all_link).to_have_class(re.compile(r"selected"))

        active_link.click()
        expect(todo_page).to_have_url(re.compile(r"#/active$"))
        expect(active_link).to_have_class(re.compile(r"selected"))
        expect(all_link).not_to_have_class(re.compile(r"selected"))

        completed_link.click()
        expect(todo_page).to_have_url(re.compile(r"#/completed$"))
        expect(completed_link).to_have_class(re.compile(r"selected"))
        expect(active_link).not_to_have_class(re.compile(r"selected"))

        all_link.click()
        expect(todo_page).to_have_url(re.compile(r"#/$"))
        expect(all_link).to_have_class(re.compile(r"selected"))

    def test_active_and_completed_show_only_matching_items(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        toggle_item(todo_items(todo_page).nth(1))  # 完成第二条

        todo_page.get_by_role("link", name="Active").click()
        expect(todo_items(todo_page)).to_have_count(2)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0], TODO_ITEMS[2]])

        todo_page.get_by_role("link", name="Completed").click()
        expect(todo_items(todo_page)).to_have_count(1)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[1]])

        todo_page.get_by_role("link", name="All").click()
        expect(todo_items(todo_page)).to_have_count(3)

    def test_new_todo_visible_immediately_in_active_view(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        toggle_item(todo_items(todo_page).nth(1))

        todo_page.get_by_role("link", name="Active").click()
        expect(todo_items(todo_page)).to_have_count(2)

        add_todo(todo_page, "water the plants")

        expect(todo_items(todo_page)).to_have_count(3)
        expect(todo_titles(todo_page)).to_have_text(
            [TODO_ITEMS[0], TODO_ITEMS[2], "water the plants"]
        )

    def test_completing_item_in_active_view_removes_it(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)

        todo_page.get_by_role("link", name="Active").click()
        expect(todo_items(todo_page)).to_have_count(3)

        # 这里用 click 而不是 check：勾选后该条会立刻被过滤掉、从 DOM 中移除，
        # check() 会一直等待「元素已勾选」这个状态，从而超时
        todo_items(todo_page).nth(0).locator(".toggle").click()

        expect(todo_items(todo_page)).to_have_count(2)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[1], TODO_ITEMS[2]])
        expect(todo_count(todo_page)).to_have_text("2 items left")

    def test_filter_persists_after_reload(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        toggle_item(todo_items(todo_page).nth(0))

        todo_page.get_by_role("link", name="Completed").click()
        expect(todo_page).to_have_url(re.compile(r"#/completed$"))

        todo_page.reload()

        expect(todo_page.get_by_role("link", name="Completed")).to_have_class(
            re.compile(r"selected")
        )
        expect(todo_items(todo_page)).to_have_count(1)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0]])


class TestClearCompleted:
    """7. Clear completed"""

    def test_hidden_until_something_is_completed(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        expect(clear_completed(todo_page)).to_be_hidden()

        toggle_item(todo_items(todo_page).nth(0))

        expect(clear_completed(todo_page)).to_be_visible()

    def test_clears_only_completed_items(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        toggle_item(todo_items(todo_page).nth(1))

        clear_completed(todo_page).click()

        expect(todo_items(todo_page)).to_have_count(2)
        expect(todo_titles(todo_page)).to_have_text([TODO_ITEMS[0], TODO_ITEMS[2]])
        expect(todo_count(todo_page)).to_have_text("2 items left")
        expect(clear_completed(todo_page)).to_be_hidden()

    def test_clearing_all_completed_resets_ui(self, todo_page: Page):
        add_todos(todo_page, TODO_ITEMS)
        toggle_all(todo_page).check()

        clear_completed(todo_page).click()

        expect(todo_items(todo_page)).to_have_count(0)
        expect(main_section(todo_page)).to_be_hidden()
        expect(footer(todo_page)).to_be_hidden()
        expect(new_todo(todo_page)).to_be_visible()
