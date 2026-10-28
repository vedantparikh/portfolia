import { expect, test } from "@playwright/test";

const username = process.env.E2E_USERNAME || "e2e";
const password = process.env.E2E_PASSWORD || "E2e!Passw0rd1";

test("sign in, keep the session across a reload, create a portfolio, sign out", async ({
  page,
}) => {
  await page.goto("/portfolio");
  await expect(page).toHaveURL(/\/login/);

  await page.getByPlaceholder("Enter your username").fill(username);
  await page.getByPlaceholder("Enter your password").fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();

  await expect(page).toHaveURL(/\/portfolio/);
  await expect(page.getByRole("heading", { name: "Portfolio", level: 1 }).last()).toBeVisible();

  const cookies = await page.context().cookies();
  const refresh = cookies.find((cookie) => cookie.name === "portfolia_refresh");
  expect(refresh?.httpOnly).toBe(true);
  expect(
    await page.evaluate(() => [localStorage.getItem("access_token"), localStorage.getItem("refresh_token"), document.cookie]),
  ).toEqual([null, null, ""]);

  await page.reload();
  await expect(page).toHaveURL(/\/portfolio/);
  await expect(page.getByRole("heading", { name: "Portfolio", level: 1 }).last()).toBeVisible();

  const name = `E2E ${Date.now()}`;
  await page.getByRole("button", { name: /New Portfolio|Create Portfolio/ }).first().click();
  await page.getByPlaceholder("e.g., My Growth Portfolio").fill(name);
  await page.getByRole("button", { name: "Create Portfolio", exact: true }).last().click();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  for (const [path, heading] of [
    ["/dashboard", /Welcome back/],
    ["/transactions", "Transactions"],
    ["/assets", "Asset Analysis"],
    ["/watchlist", "Watchlists"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
  }

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
