// @ts-check
/**
 * 项目知识：勾选框的 check() / uncheck() 与 click() 怎么选
 *
 * 默认用 check() / uncheck()：它除了点击，还会回读并断言元素最终处于勾选（或未勾选）
 * 状态，语义更强，能顺带覆盖「状态是否真的切换成功」。
 *
 * 但当这次操作会导致元素从 DOM 中消失时，必须改用 click()。例如
 * 「6. 过滤器 › Active 视图下勾选完成，该条从列表中消失」：勾选后该条立即被过滤掉、
 * 脱离 DOM，而 check() 内部要等待的「元素已勾选」这个状态永远不会出现，于是会一直
 * 重试到 30s 超时（而不是快速失败，报错信息也只会指向 check 本身，容易误导）。
 * 这类场景的写法是：用 click() 触发操作，再用业务结果断言（条目数量、列表内容）验证。
 *
 * 判断标准：操作之后元素是否还在页面上。还在 → check()；会被移除 → click()。
 */
const { test, expect } = require('@playwright/test');

const TODO_ITEMS = ['buy some cheese', 'feed the cat', 'book a doctors appointment'];

// ---- 定位辅助 ----
/** 新建 todo 的输入框 */
const newTodo = (page) => page.locator('.new-todo');
/** 列表里所有 todo 条目 */
const todoItems = (page) => page.locator('.todo-list li');
/** 每条 todo 的标题文本 */
const todoTitles = (page) => page.locator('.todo-list li label');
/** 已完成条目 */
const completedItems = (page) => page.locator('.todo-list li.completed');
/** 左侧「全部完成」勾选框 */
const toggleAll = (page) => page.locator('.toggle-all');
/** 剩余计数 */
const todoCount = (page) => page.locator('.todo-count');
/** 主列表区 / 底栏，无数据时整个不渲染 */
const mainSection = (page) => page.locator('.main');
const footer = (page) => page.locator('.footer');
/** Clear completed 按钮 */
const clearCompleted = (page) => page.getByRole('button', { name: 'Clear completed' });

// ---- 操作辅助 ----
async function addTodo(page, text) {
  await newTodo(page).fill(text);
  await newTodo(page).press('Enter');
}

async function addTodos(page, items) {
  for (const text of items) await addTodo(page, text);
}

/** 双击条目进入编辑态，返回该条目的 .edit 输入框 */
async function startEditing(item, text) {
  await item.locator('label').dblclick();
  const editInput = item.locator('.edit');
  await expect(editInput).toBeVisible();
  if (text !== undefined) await editInput.fill(text);
  return editInput;
}

/** 勾选某个条目 */
async function toggleItem(item) {
  await item.locator('.toggle').check();
}

test.beforeEach(async ({ page }) => {
  // baseURL 已指向 .../todomvc/，用 './' 保持路径（'/' 会跑到域名根目录）
  await page.goto('./');
});

test.describe('1. 初始状态', () => {
  test('输入框可见、带 placeholder 且自动聚焦', async ({ page }) => {
    await expect(newTodo(page)).toBeVisible();
    await expect(newTodo(page)).toHaveAttribute('placeholder', 'What needs to be done?');
    await expect(newTodo(page)).toBeFocused();
  });

  test('没有 todo 时列表区和底栏都不展示', async ({ page }) => {
    await expect(todoItems(page)).toHaveCount(0);
    await expect(mainSection(page)).toBeHidden();
    await expect(footer(page)).toBeHidden();
  });

  test('没有 todo 时不展示 Clear completed', async ({ page }) => {
    await expect(clearCompleted(page)).toBeHidden();
  });
});

test.describe('2. 新增 todo', () => {
  test('输入文本按 Enter 新增一条，列表区和底栏出现', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);

    await expect(todoItems(page)).toHaveCount(1);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0]]);
    await expect(todoCount(page)).toHaveText('1 item left');
    await expect(mainSection(page)).toBeVisible();
    await expect(footer(page)).toBeVisible();
  });

  test('新增后输入框被清空', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);

    await expect(newTodo(page)).toHaveValue('');
  });

  test('可以连续新增多条，并按添加顺序排列', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);

    await expect(todoItems(page)).toHaveCount(3);
    await expect(todoTitles(page)).toHaveText(TODO_ITEMS);
    await expect(todoCount(page)).toHaveText('3 items left');
  });

  test('首尾空白会被 trim', async ({ page }) => {
    await addTodo(page, `   ${TODO_ITEMS[0]}   `);

    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0]]);
  });

  test('空输入或纯空格不产生新条目', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    await addTodo(page, '');
    await addTodo(page, '     ');

    await expect(todoItems(page)).toHaveCount(1);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0]]);
  });
});

test.describe('3. 完成状态切换', () => {
  test('勾选单条标记为完成，计数递减', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const first = todoItems(page).nth(0);

    await toggleItem(first);

    await expect(first).toHaveClass(/completed/);
    await expect(first.locator('.toggle')).toBeChecked();
    await expect(completedItems(page)).toHaveCount(1);
    await expect(todoCount(page)).toHaveText('2 items left');
  });

  test('再次点击可以取消完成', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    await toggleItem(item);
    await expect(item).toHaveClass(/completed/);

    await item.locator('.toggle').uncheck();

    await expect(item).not.toHaveClass(/completed/);
    await expect(completedItems(page)).toHaveCount(0);
    await expect(todoCount(page)).toHaveText('1 item left');
  });

  test('计数文案的单复数正确', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    await expect(todoCount(page)).toHaveText('1 item left');

    await addTodo(page, TODO_ITEMS[1]);
    await expect(todoCount(page)).toHaveText('2 items left');
  });

  test('toggle-all 可以一次性全部完成、再全部取消', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);

    await toggleAll(page).check();

    await expect(completedItems(page)).toHaveCount(3);
    await expect(todoCount(page)).toHaveText('0 items left');

    await toggleAll(page).uncheck();

    await expect(completedItems(page)).toHaveCount(0);
    await expect(todoCount(page)).toHaveText('3 items left');
  });

  test('逐条勾满后 toggle-all 自动选中，取消一条后自动取消', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    for (let i = 0; i < TODO_ITEMS.length; i++) {
      await toggleItem(todoItems(page).nth(i));
    }
    await expect(toggleAll(page)).toBeChecked();

    await todoItems(page).nth(1).locator('.toggle').uncheck();

    await expect(toggleAll(page)).not.toBeChecked();
    await expect(todoCount(page)).toHaveText('1 item left');
  });
});

test.describe('4. 编辑', () => {
  test('双击进入编辑态，并带出原文本', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    const editInput = await startEditing(item);

    await expect(item).toHaveClass(/editing/);
    await expect(editInput).toHaveValue(TODO_ITEMS[0]);
  });

  test('修改后按 Enter 保存并退出编辑态', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    const editInput = await startEditing(item, 'buy some sausages');
    await editInput.press('Enter');

    await expect(item).not.toHaveClass(/editing/);
    await expect(todoTitles(page)).toHaveText(['buy some sausages']);
    await expect(todoCount(page)).toHaveText('1 item left');
  });

  test('修改后点击别处失焦保存', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    await startEditing(item, 'buy some sausages');
    await page.getByRole('heading', { name: 'todos' }).click();

    await expect(item).not.toHaveClass(/editing/);
    await expect(todoTitles(page)).toHaveText(['buy some sausages']);
  });

  test('按 Esc 放弃修改，保存的是原文本', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    const editInput = await startEditing(item, 'buy some sausages');
    await editInput.press('Escape');
    // 不论 Esc 是否直接退出编辑态，最终落库的都应该是原文本
    await page.getByRole('heading', { name: 'todos' }).click();

    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0]]);
  });

  test('编辑为空并保存会删除该条', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const item = todoItems(page).nth(0);

    const editInput = await startEditing(item, '');
    await editInput.press('Enter');

    await expect(todoItems(page)).toHaveCount(2);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[1], TODO_ITEMS[2]]);
  });

  test('编辑一条不影响其他条目的完成状态', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const second = todoItems(page).nth(1);
    await toggleItem(second);

    const first = todoItems(page).nth(0);
    const editInput = await startEditing(first, 'buy some sausages');
    await editInput.press('Enter');

    await expect(todoTitles(page)).toHaveText(['buy some sausages', TODO_ITEMS[1], TODO_ITEMS[2]]);
    await expect(second).toHaveClass(/completed/);
    await expect(second.locator('.toggle')).toBeChecked();
    await expect(todoCount(page)).toHaveText('2 items left');
  });
});

test.describe('5. 删除', () => {
  test('hover 后点击删除按钮移除该条，计数更新', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const second = todoItems(page).nth(1);

    await second.hover();
    await second.getByRole('button', { name: 'Delete' }).click();

    await expect(todoItems(page)).toHaveCount(2);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0], TODO_ITEMS[2]]);
    await expect(todoCount(page)).toHaveText('2 items left');
  });

  test('删除中间一条不影响其余条目的顺序', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const first = todoItems(page).nth(0);

    await first.hover();
    await first.getByRole('button', { name: 'Delete' }).click();

    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[1], TODO_ITEMS[2]]);
  });

  test('删除最后一条后列表区和底栏重新隐藏', async ({ page }) => {
    await addTodo(page, TODO_ITEMS[0]);
    const item = todoItems(page).nth(0);

    await item.hover();
    await item.getByRole('button', { name: 'Delete' }).click();

    await expect(todoItems(page)).toHaveCount(0);
    await expect(mainSection(page)).toBeHidden();
    await expect(footer(page)).toBeHidden();
  });
});

test.describe('6. 过滤器', () => {
  test('三个过滤器链接可切换，当前项高亮', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    const allLink = page.getByRole('link', { name: 'All' });
    const activeLink = page.getByRole('link', { name: 'Active' });
    const completedLink = page.getByRole('link', { name: 'Completed' });

    await expect(allLink).toHaveClass(/selected/);

    await activeLink.click();
    await expect(page).toHaveURL(/#\/active$/);
    await expect(activeLink).toHaveClass(/selected/);
    await expect(allLink).not.toHaveClass(/selected/);

    await completedLink.click();
    await expect(page).toHaveURL(/#\/completed$/);
    await expect(completedLink).toHaveClass(/selected/);
    await expect(activeLink).not.toHaveClass(/selected/);

    await allLink.click();
    await expect(page).toHaveURL(/#\/$/);
    await expect(allLink).toHaveClass(/selected/);
  });

  test('Active 只显示未完成，Completed 只显示已完成', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await toggleItem(todoItems(page).nth(1)); // 完成第二条

    await page.getByRole('link', { name: 'Active' }).click();
    await expect(todoItems(page)).toHaveCount(2);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0], TODO_ITEMS[2]]);

    await page.getByRole('link', { name: 'Completed' }).click();
    await expect(todoItems(page)).toHaveCount(1);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[1]]);

    await page.getByRole('link', { name: 'All' }).click();
    await expect(todoItems(page)).toHaveCount(3);
  });

  test('Active 视图下新增的 todo 立即可见', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await toggleItem(todoItems(page).nth(1));

    await page.getByRole('link', { name: 'Active' }).click();
    await expect(todoItems(page)).toHaveCount(2);

    await addTodo(page, 'water the plants');

    await expect(todoItems(page)).toHaveCount(3);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0], TODO_ITEMS[2], 'water the plants']);
  });

  test('Active 视图下勾选完成，该条从列表中消失', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);

    await page.getByRole('link', { name: 'Active' }).click();
    await expect(todoItems(page)).toHaveCount(3);

    // 这里用 click 而不是 check：勾选后该条会立刻被过滤掉、从 DOM 中移除，
    // check() 会一直等待「元素已勾选」这个状态，从而超时
    await todoItems(page).nth(0).locator('.toggle').click();

    await expect(todoItems(page)).toHaveCount(2);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[1], TODO_ITEMS[2]]);
    await expect(todoCount(page)).toHaveText('2 items left');
  });

  test('刷新页面后过滤器状态保持', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await toggleItem(todoItems(page).nth(0));

    await page.getByRole('link', { name: 'Completed' }).click();
    await expect(page).toHaveURL(/#\/completed$/);

    await page.reload();

    await expect(page.getByRole('link', { name: 'Completed' })).toHaveClass(/selected/);
    await expect(todoItems(page)).toHaveCount(1);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0]]);
  });
});

test.describe('7. Clear completed', () => {
  test('没有已完成项时不展示，有则展示', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await expect(clearCompleted(page)).toBeHidden();

    await toggleItem(todoItems(page).nth(0));

    await expect(clearCompleted(page)).toBeVisible();
  });

  test('点击后只清除已完成项，未完成项保留', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await toggleItem(todoItems(page).nth(1));

    await clearCompleted(page).click();

    await expect(todoItems(page)).toHaveCount(2);
    await expect(todoTitles(page)).toHaveText([TODO_ITEMS[0], TODO_ITEMS[2]]);
    await expect(todoCount(page)).toHaveText('2 items left');
    await expect(clearCompleted(page)).toBeHidden();
  });

  test('全部完成后清除，界面回到初始状态', async ({ page }) => {
    await addTodos(page, TODO_ITEMS);
    await toggleAll(page).check();

    await clearCompleted(page).click();

    await expect(todoItems(page)).toHaveCount(0);
    await expect(mainSection(page)).toBeHidden();
    await expect(footer(page)).toBeHidden();
    await expect(newTodo(page)).toBeVisible();
  });
});
