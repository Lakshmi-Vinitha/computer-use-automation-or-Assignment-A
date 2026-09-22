"""
Playwright Surface Adapter implementation for Web applications.
"""

import base64
import logging
from typing import Optional, List
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page, Locator as PWLocator

from src.surfaces.base import SurfaceAdapter
from src.models.actions import Locator, Observation, ElementInfo

logger = logging.getLogger(__name__)


class PlaywrightSurfaceAdapter(SurfaceAdapter):
    def __init__(self, headless: bool = True, page: Optional[Page] = None):
        self.headless = headless
        self._external_page = page is not None
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = page

    async def initialize(self) -> None:
        if self.page:
            return
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.page = await self.context.new_page()

    async def close(self) -> None:
        if self._external_page:
            return
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.page = None

    async def _resolve_working_locator(self, locator: Locator) -> PWLocator:
        """
        Evaluate locator strategies in priority cascade order:
        role_name -> label -> text -> css -> xpath
        Returns the first strategy that matches an active DOM element.
        """
        if not self.page:
            raise RuntimeError("Adapter page is not initialized")

        candidates: List[PWLocator] = []

        if locator.role_name and "role" in locator.role_name and "name" in locator.role_name:
            role = locator.role_name["role"]
            name = locator.role_name["name"]
            try:
                candidates.append(self.page.get_by_role(role, name=name))
            except Exception:
                pass

        if locator.label:
            try:
                candidates.append(self.page.get_by_label(locator.label))
                candidates.append(self.page.get_by_label(locator.label, exact=False))
            except Exception:
                pass

        if locator.text:
            try:
                candidates.append(self.page.get_by_text(locator.text))
            except Exception:
                pass

        if locator.css:
            try:
                candidates.append(self.page.locator(locator.css))
            except Exception:
                pass

        if locator.xpath:
            try:
                candidates.append(self.page.locator(locator.xpath))
            except Exception:
                pass

        for cand in candidates:
            try:
                count = await cand.count()
                if count > 0:
                    return cand
            except Exception:
                continue

        if candidates:
            return candidates[-1]

        raise ValueError(f"Could not construct Playwright locator from: {locator}")

    async def observe(self) -> Observation:
        if not self.page:
            raise RuntimeError("Adapter page is not initialized")

        url = self.page.url
        title = await self.page.title()

        # Extract visible text summary
        visible_text = await self.page.evaluate("() => document.body.innerText")
        visible_text = "\n".join([line.strip() for line in visible_text.splitlines() if line.strip()])

        # Extract interactive elements summary
        interactive_elements: List[ElementInfo] = []
        raw_elements = await self.page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="button"], [role="link"]'));
            return els.map(el => {
                let labelText = '';
                if (el.id) {
                    const lbl = document.querySelector(`label[for="${el.id}"]`);
                    if (lbl) labelText = lbl.innerText.trim();
                }
                if (!labelText && el.labels && el.labels.length > 0) {
                    labelText = el.labels[0].innerText.trim();
                }
                return {
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || el.type || el.tagName.toLowerCase(),
                    name: el.innerText ? el.innerText.trim() : (el.value || el.placeholder || el.name || ''),
                    label: labelText,
                    text: el.innerText ? el.innerText.trim() : '',
                    css_selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : el.tagName.toLowerCase()),
                    is_interactive: !el.disabled
                };
            });
        }""")

        for item in raw_elements:
            interactive_elements.append(ElementInfo(**item))

        # Capture screenshot base64
        screenshot_bytes = await self.page.screenshot(type="jpeg", quality=60)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        return Observation(
            url=url,
            title=title,
            interactive_elements=interactive_elements,
            accessibility_tree_text=f"Page Title: {title}\nURL: {url}\nVisible Text Content:\n{visible_text}",
            visible_text_summary=visible_text[:2000],
            screenshot_base64=screenshot_b64
        )

    async def click(self, locator: Locator, timeout_ms: int = 5000) -> bool:
        try:
            pw_loc = await self._resolve_working_locator(locator)
            await pw_loc.first.click(timeout=timeout_ms)
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=2000)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.warning(f"Click failed for locator {locator}: {e}")
            return False

    async def type(self, locator: Locator, text: str, timeout_ms: int = 5000) -> bool:
        try:
            pw_loc = await self._resolve_working_locator(locator)
            await pw_loc.first.fill(text, timeout=timeout_ms)
            return True
        except Exception as e:
            logger.warning(f"Type failed for locator {locator}: {e}")
            return False

    async def navigate(self, url: str) -> bool:
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logger.warning(f"Navigate to {url} failed: {e}")
            return False

    async def extract(self, locator: Locator) -> Optional[str]:
        try:
            pw_loc = await self._resolve_working_locator(locator)
            return await pw_loc.first.inner_text()
        except Exception as e:
            logger.warning(f"Extract failed for locator {locator}: {e}")
            return None

    async def screenshot(self) -> bytes:
        if not self.page:
            raise RuntimeError("Adapter page is not initialized")
        return await self.page.screenshot(type="png")

    async def wait_for_selector(self, locator: Locator, timeout_ms: int = 5000) -> bool:
        try:
            pw_loc = await self._resolve_working_locator(locator)
            await pw_loc.first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            return False
