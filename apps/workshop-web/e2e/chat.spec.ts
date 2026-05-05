import { test, expect } from "@playwright/test";

test.describe("Chat Flow", () => {
  test("redirects to /chat from root", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/chat/);
  });

  test("shows empty state on /chat", async ({ page }) => {
    await page.goto("/chat");
    await expect(
      page.getByRole("heading", { name: /start a conversation/i }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /new chat/i })).toBeVisible();
  });

  test("health badge is visible", async ({ page }) => {
    await page.goto("/chat");
    const badge = page.getByRole("status");
    await expect(badge).toBeVisible();
  });

  test("creates a new conversation and navigates to it", async ({ page }) => {
    await page.goto("/chat");

    const newChatBtn = page.getByRole("button", { name: /new chat/i });
    await newChatBtn.click();

    await expect(page).toHaveURL(/\/chat\/[^/]+$/);

    await expect(
      page.getByText(/start this conversation/i),
    ).toBeVisible();
  });

  test("composer textarea is present on conversation page", async ({
    page,
  }) => {
    await page.goto("/chat");

    const newChatBtn = page.getByRole("button", { name: /new chat/i });
    await newChatBtn.click();

    await expect(page.getByPlaceholder(/ask rain anything/i)).toBeVisible();
  });

  test("sidebar shows conversations after creation", async ({ page }) => {
    await page.goto("/chat");

    const newChatBtn = page.getByRole("button", { name: /new chat/i });
    await newChatBtn.click();
    await expect(page).toHaveURL(/\/chat\/[^/]+$/);

    const sidebar = page.getByRole("navigation", { name: /conversations/i });
    await expect(sidebar).toBeVisible();
  });
});