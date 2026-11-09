"""Browser checks for services → calculator → contacts. No real submissions."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit
import itertools
import os
import re
import shutil
import unittest

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    "landing": ("Лендинг", 35000),
    "corporate": ("Корпоративный сайт", 80000),
    "design": ("Дизайн интерфейса", 30000),
    "layout": ("Адаптивная вёрстка", 25000),
    "redesign": ("Редизайн", 45000),
}
WIDTHS = (375, 768, 1024)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class ServiceFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT.parent))
        )
        Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/{ROOT.name}/"
        cls.playwright = sync_playwright().start()
        executable = os.environ.get("BROWSER_PATH") or shutil.which("chromium")
        try:
            cls.browser = cls.playwright.chromium.launch(
                executable_path=executable, headless=True, args=["--no-sandbox"]
            )
        except Exception:
            cls.playwright.stop()
            cls.server.shutdown()
            cls.server.server_close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.errors = []
        self.external_requests = []
        self.non_get_requests = []
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        self.context.route("**/*", self.local_only)
        self.context.on("request", self.record_request)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda message: self.errors.append(message.text)
                     if message.type == "error" else None)

    def local_only(self, route):
        # A test must never send a message to Formspree or another external host.
        if route.request.url.startswith(self.base):
            route.continue_()
        else:
            self.external_requests.append(route.request.url)
            route.abort()

    def record_request(self, request):
        if request.method != "GET":
            self.non_get_requests.append((request.method, request.url))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "JavaScript/console errors")
        self.assertEqual(self.external_requests, [], "Unexpected external request")
        self.assertEqual(self.non_get_requests, [], "Unexpected automatic submission")

    def open(self, path):
        response = self.page.goto(self.base + path)
        self.assertEqual(response.status, 200)

    def assert_initial(self, project):
        expect(self.page.locator(f"#project-{project}")).to_be_checked()
        expect(self.page.locator("#page-count")).to_have_value("1")
        expect(self.page.locator("[name=extra]:checked")).to_have_count(0)
        expect(self.page.locator("#estimate-total")).to_have_text(
            re.compile(r"^\D*" + r"\D*".join(str(PROJECTS[project][1])) + r"\D*$")
        )
        expect(self.page.locator(".book-spread")).to_have_attribute("data-book-page", "1")
        expect(self.page.get_by_role("button", name="На страницу назад", exact=True)).to_be_disabled()
        expect(self.page.get_by_role("button", name="На страницу вперёд", exact=True)).to_be_enabled()

    def test_five_service_links_and_reset_at_mobile_widths(self):
        for width in WIDTHS:
            self.page.set_viewport_size({"width": width, "height": 1000})
            for index, (project, (_, price)) in enumerate(PROJECTS.items()):
                with self.subTest(width=width, project=project):
                    self.open("services.html")
                    link = self.page.locator(".service-card").nth(index).locator(".service-action")
                    expect(link).to_have_attribute("href", f"./calculator.html?project={project}")
                    link.click()
                    self.page.wait_for_url(self.base + f"calculator.html?project={project}")
                    self.assert_initial(project)
                    self.page.locator("#page-count").focus()
                    self.page.keyboard.press("ArrowRight")
                    self.page.locator("#extra-animations").check()
                    self.assertEqual(self.money(), price + 5000 + 10000)
                    alternate = "corporate" if project == "landing" else "landing"
                    self.page.locator(f"#project-{alternate}").check()
                    self.assertEqual(self.money(), PROJECTS[alternate][1] + 15000)
                    self.page.get_by_role("button", name="Сбросить выбор").click()
                    self.assert_initial(project)

    def money(self):
        return int(re.sub(r"\D", "", self.page.locator("#estimate-total").inner_text()))

    def test_direct_open_and_untrusted_project(self):
        self.open("calculator.html")
        self.assert_initial("landing")
        self.page.locator("#project-redesign").check()
        self.page.locator("#extra-seo").check()
        self.page.get_by_role("button", name="Сбросить выбор").click()
        self.assert_initial("landing")
        for project in ("unknown", "support", "", "LANDING", "constructor", "__proto__",
                        '<img src=x onerror="window.injected=true">', 'corporate\"]'):
            with self.subTest(project=project):
                self.open("calculator.html?" + urlencode({"project": project}))
                self.assert_initial("landing")
                self.page.locator("#project-design").check()
                self.page.get_by_role("button", name="Сбросить выбор").click()
                self.assert_initial("landing")
                self.assertTrue(self.page.evaluate("window.injected === undefined"))
        # Only project is imported here; names, free text, prices and extras are ignored.
        self.open("calculator.html?" + urlencode({"project": "design", "pages": "15",
                  "seo": "1", "total": "1", "name": "Чужое имя", "message": "Чужой текст"}))
        self.assert_initial("design")
        self.open("calculator.html?project=corporate&project=design")
        self.assert_initial("corporate")

    def test_calculator_to_contacts_for_every_project(self):
        for project, (name, price) in PROJECTS.items():
            with self.subTest(project=project):
                self.open(f"calculator.html?project={project}")
                self.page.locator("#page-count").evaluate(
                    'el => {el.value="3";el.dispatchEvent(new Event("input",{bubbles:true}));}'
                )
                self.page.locator("#extra-animations").check()
                self.page.locator("#extra-form").check()
                self.assertEqual(self.money(), price + 25000)
                link = self.page.locator("#discuss-estimate")
                query = parse_qs(urlsplit(link.get_attribute("href")).query)
                self.assertEqual(query, {"source": ["calculator"], "project": [project],
                                        "pages": ["3"], "animations": ["1"], "form": ["1"]})
                link.click()
                self.page.wait_for_url("**/contact.html?**")
                message = self.page.locator("#message").input_value()
                self.assertIn(f"Тип проекта: {name}.", message)
                self.assertIn("Количество страниц: 3.", message)
                total_line = next(line for line in message.splitlines() if line.startswith("Ориентировочная стоимость:"))
                self.assertEqual(int(re.sub(r"\D", "", total_line)), price + 25000)
                expect(self.page.locator("#estimate-prefill-note")).to_be_visible()
                expect(self.page.locator("#message")).to_have_attribute("aria-describedby", "estimate-prefill-note")
                expect(self.page.locator("#support-prefill-note")).to_be_hidden()
                self.assert_form()
                self.page.locator("#message").fill("Мой уточнённый запрос")
                self.page.locator("#name").fill("Тест")
                self.page.locator("#email").fill("invalid-email")
                self.page.get_by_role("button", name="Отправить", exact=True).click()
                self.assertTrue(self.page.locator("#email").evaluate("el=>el.validity.typeMismatch"))
                expect(self.page.locator("#message")).to_have_value("Мой уточнённый запрос")

    def assert_form(self):
        expect(self.page.locator("#contact-form")).to_have_attribute("data-formspree-id", "mbggbnwq")
        expect(self.page.locator("#contact-form")).to_have_attribute("action", "https://formspree.io/f/mbggbnwq")
        expect(self.page.locator("#name")).to_have_value("")
        expect(self.page.locator("#email")).to_have_value("")

    def test_support_stays_monthly_and_bypasses_calculator(self):
        for width in WIDTHS:
            self.page.set_viewport_size({"width": width, "height": 1000})
            self.open("services.html")
            support = self.page.locator(".service-card").nth(5)
            self.assertIn("8 000 ₽ / мес.", support.inner_text())
            expect(support.locator('a[href*="calculator"]')).to_have_count(0)
            support.locator(".service-action").click()
            self.page.wait_for_url(self.base + "contact.html?service=support")
            message = self.page.locator("#message").input_value()
            self.assertIn("поддержку и развитие сайта", message)
            self.assertIn("8 000 ₽ в месяц", message)
            expect(self.page.locator("#support-prefill-note")).to_be_visible()
            expect(self.page.locator("#message")).to_have_attribute("aria-describedby", "support-prefill-note")
            expect(self.page.locator("#estimate-prefill-note")).to_be_hidden()
            self.assert_form()
        self.open("contact.html?" + urlencode({"service": "support", "name": "Не импортировать",
                  "email": "test@example.com", "message": "Текст из адреса"}))
        self.assertNotIn("Текст из адреса", self.page.locator("#message").input_value())
        self.assert_form()

    def test_contact_validation_and_mixed_parameters(self):
        invalid = [
            {"service": "unknown"}, {"service": '<img src=x onerror="window.injected=true">'},
            {"source": "calculator", "project": "constructor", "pages": "1"},
            {"source": "calculator", "project": "landing", "pages": "16"},
            {"source": "calculator", "project": "landing", "pages": "2", "seo": "<script>"},
            {"source": "calculator", "project": "invalid", "pages": "1", "service": "support"},
            {"message": "Не подставлять", "name": "Имя", "email": "test@example.com"},
        ]
        for params in invalid:
            with self.subTest(params=params):
                self.open("contact.html?" + urlencode(params))
                expect(self.page.locator("#message")).to_have_value("")
                self.assertIsNone(self.page.locator("#message").get_attribute("aria-describedby"))
                expect(self.page.locator("#estimate-prefill-note")).to_be_hidden()
                expect(self.page.locator("#support-prefill-note")).to_be_hidden()
                self.assert_form()
                self.assertTrue(self.page.evaluate("window.injected === undefined"))
        # A valid calculator source takes priority over a conflicting service parameter.
        self.open("contact.html?source=calculator&project=corporate&pages=2&service=support")
        self.assertIn("Тип проекта: Корпоративный сайт.", self.page.locator("#message").input_value())
        expect(self.page.locator("#support-prefill-note")).to_be_hidden()

    def test_existing_message_is_never_overwritten(self):
        html = (ROOT / "contact.html").read_text()
        saved = "Уже введённый пользователем текст"
        html = html.replace("</textarea>", saved + "</textarea>")
        self.page.route("**/contact.html?**", lambda route: route.fulfill(
            status=200, content_type="text/html; charset=utf-8", body=html
        ))
        for query in ("service=support", "source=calculator&project=design&pages=4"):
            self.open("contact.html?" + query)
            expect(self.page.locator("#message")).to_have_value(saved)
            expect(self.page.locator("#support-prefill-note")).to_be_hidden()
            expect(self.page.locator("#estimate-prefill-note")).to_be_hidden()

    def test_all_calculator_combinations(self):
        self.open("calculator.html?project=corporate")
        extras = {"animations": 10000, "form": 5000, "seo": 12000}
        cases = []
        for project, (_, price) in PROJECTS.items():
            for pages in range(1, 16):
                for flags in itertools.product((False, True), repeat=3):
                    selected = [key for key, flag in zip(extras, flags) if flag]
                    cases.append({"project": project, "pages": pages, "extras": selected,
                                  "total": price + (pages - 1) * 5000 + sum(extras[k] for k in selected)})
        checked = self.page.evaluate('''cases => {
            const form=document.querySelector('#calculator-form');
            for(const test of cases){
                form.querySelector(`[name="project"][value="${test.project}"]`).checked=true;
                form.querySelector('#page-count').value=String(test.pages);
                form.querySelectorAll('[name="extra"]').forEach(el=>el.checked=test.extras.includes(el.value));
                form.dispatchEvent(new Event('input',{bubbles:true}));
                const money=text=>Number(text.replace(/\\D/g,''));
                const total=money(document.querySelector('#estimate-total').value);
                const breakdown=[...document.querySelectorAll('#estimate-breakdown dd')].reduce((sum,el)=>sum+money(el.textContent),0);
                if(total!==test.total || breakdown!==test.total) throw new Error(JSON.stringify(test));
            }
            return cases.length;
        }''', cases)
        self.assertEqual(checked, 600)
        self.page.get_by_role("button", name="Сбросить выбор").click()
        self.assert_initial("corporate")

    def test_responsive_pages_and_existing_filters(self):
        files = sorted(ROOT.glob("*.html")) + sorted((ROOT / "articles").glob("*.html"))
        for width in WIDTHS:
            self.page.set_viewport_size({"width": width, "height": 1000})
            for file in files:
                self.open(str(file.relative_to(ROOT)))
                self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
                                f"Overflow: {file.name} at {width}px")
                self.page.locator(".menu-toggle").click()
                expect(self.page.locator("#main-nav a:visible")).to_have_count(7)
                self.page.keyboard.press("Escape")
                expect(self.page.locator(".menu-toggle")).to_have_attribute("aria-expanded", "false")
                self.assertTrue(self.page.locator(".menu-toggle").evaluate("el=>el===document.activeElement"))
            self.open("services.html")
            for details in self.page.locator(".service-details").all():
                summary = details.locator("summary")
                summary.focus()
                self.page.keyboard.press("Enter")
                self.assertTrue(details.evaluate("el=>el.open"))
                self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                self.page.keyboard.press("Space")
                self.assertFalse(details.evaluate("el=>el.open"))
        self.open("blog.html")
        self.page.locator("#blog-search").fill("GitHub")
        expect(self.page.locator("[data-blog-category]:visible")).to_have_count(1)
        self.page.locator('[data-blog-filter="development"]').click()
        expect(self.page.locator("#blog-empty")).to_be_visible()
        self.page.get_by_role("button", name="Сбросить", exact=True).click()
        expect(self.page.locator("[data-blog-category]:visible")).to_have_count(3)
        self.open("portfolio.html")
        for category, count in (("landing", 2), ("corporate", 2), ("design", 2), ("all", 6)):
            self.page.locator(f'[data-filter="{category}"]').click()
            expect(self.page.locator("[data-category]:visible")).to_have_count(count)

    def test_book_animation_and_reduced_motion(self):
        self.open("calculator.html?project=design")
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.get_by_role("button", name="На страницу вперёд", exact=True).click()
        expect(self.page.locator(".book-spread")).to_have_attribute("data-book-page", "2")
        self.page.get_by_role("button", name="На страницу назад", exact=True).click()
        expect(self.page.locator(".book-spread")).to_have_attribute("data-book-page", "1")
        expect(self.page.get_by_role("button", name="На страницу назад", exact=True)).to_be_disabled()
        expect(self.page.get_by_role("button", name="На страницу вперёд", exact=True)).to_be_enabled()
        self.page.locator("#page-count").focus()
        self.page.keyboard.press("End")
        self.page.emulate_media(reduced_motion="reduce")
        expect(self.page.locator(".book-spread")).to_have_attribute("data-book-page", "15")
        expect(self.page.get_by_role("button", name="На страницу вперёд", exact=True)).to_be_disabled()
        self.page.get_by_role("button", name="Сбросить выбор").click()
        self.assert_initial("design")

    def test_service_accordion_exclusivity_and_card_heights(self):
        for width in (*WIDTHS, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 1000})
                self.open("services.html")
                heights = self.page.locator(".service-card").evaluate_all(
                    "els=>els.map(el=>el.getBoundingClientRect().height)"
                )
                for index in range(6):
                    details = self.page.locator(".service-details").nth(index)
                    summary = details.locator("summary")
                    if index % 2:
                        summary.focus()
                        self.page.keyboard.press("Enter")
                    else:
                        # On a phone the previous overlay can cover the next summary.
                        # Dismiss it before testing a pointer click on the lower card.
                        if index:
                            self.page.keyboard.press("Escape")
                            expect(self.page.locator(".service-details[open]")).to_have_count(0)
                        summary.click()
                    expect(self.page.locator(".service-details[open]")).to_have_count(1)
                    self.assertTrue(details.evaluate("el=>el.open"))
                    # A neighbouring card must keep its original closed height.
                    self.page.wait_for_function("""heights=>[...document.querySelectorAll('.service-card')].every(
                        (card,index)=>card.querySelector('details').open || Math.abs(card.getBoundingClientRect().height-heights[index])<1
                    )""", arg=heights)
                self.page.keyboard.press("Space")
                expect(self.page.locator(".service-details[open]")).to_have_count(0)
                self.assertTrue(summary.evaluate("el=>el===document.activeElement"))
                self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        # Rapid changes settle on the last requested panel without multiple open items.
        self.page.locator(".services-grid").evaluate("""grid=>{
            const buttons=grid.querySelectorAll('.service-details summary');
            for(const index of [0,1,2,1,0,0,5]) buttons[index].click();
        }""")
        expect(self.page.locator(".service-details[open]")).to_have_count(1)
        self.assertTrue(self.page.locator(".service-details").nth(5).evaluate("el=>el.open"))

    def test_service_overlay_keeps_grid_positions_and_covers_lower_card(self):
        for width in (*WIDTHS, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 1000})
                self.open("services.html")
                expect(self.page.locator(".services-grid.is-layered")).to_have_count(1)
                positions = """grid=>({
                    height:grid.getBoundingClientRect().height,
                    cards:[...grid.querySelectorAll('.service-card-slot')].map(el=>({
                        top:el.getBoundingClientRect().top-grid.getBoundingClientRect().top,
                        height:el.getBoundingClientRect().height
                    })),
                    note:document.querySelector('.price-note').getBoundingClientRect().top-grid.getBoundingClientRect().top
                })"""
                grid = self.page.locator(".services-grid")
                before = grid.evaluate(positions)
                summary = self.page.locator(".service-details summary").first
                summary.click()
                expect(self.page.locator(".service-details[open]")).to_have_count(1)
                after = grid.evaluate(positions)
                self.assertAlmostEqual(before["height"], after["height"], delta=1)
                self.assertAlmostEqual(before["note"], after["note"], delta=1)
                for old, new in zip(before["cards"], after["cards"]):
                    self.assertAlmostEqual(old["top"], new["top"], delta=1)
                    self.assertAlmostEqual(old["height"], new["height"], delta=1)
                first = self.page.locator(".service-card").first
                self.assertGreater(first.bounding_box()["height"], before["cards"][0]["height"] + 100)
                self.assertNotEqual(first.evaluate("el=>getComputedStyle(el).boxShadow"), "none")
                columns = grid.evaluate("el=>getComputedStyle(el).gridTemplateColumns.split(' ').length")
                lower = self.page.locator(".service-card").nth(columns)
                lower.evaluate("el=>el.scrollIntoView({block:'center',behavior:'instant'})")
                # Hit testing proves that the expanded card is above the next row.
                covered_by_first = lower.evaluate("""el=>{
                    const box=el.getBoundingClientRect();
                    return document.elementFromPoint(box.x+box.width/2,box.y+16)?.closest('.service-card')===document.querySelector('.service-card');
                }""")
                self.assertTrue(covered_by_first)
                self.page.keyboard.press("Escape")
                expect(self.page.locator(".service-details[open]")).to_have_count(0)
                expect(summary).to_be_focused()
                # Tab/focus to a covered card must expose the new focus target.
                summary.press("Enter")
                lower.locator(".service-action").focus()
                expect(self.page.locator(".service-details[open]")).to_have_count(0)
                expect(lower.locator(".service-action")).to_be_focused()
                summary.focus()
                self.page.keyboard.press("Enter")
                self.page.locator("h1").click()
                expect(self.page.locator(".service-details[open]")).to_have_count(0)
                self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth<=innerWidth"))

    def test_service_overlay_resizes_with_open_card(self):
        self.open("services.html")
        summary = self.page.locator(".service-details summary").first
        summary.click()
        for width in (768, 375, 1024, 1440):
            self.page.set_viewport_size({"width": width, "height": 1000})
            expect(self.page.locator(".service-details[open]")).to_have_count(1)
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth<=innerWidth"))
            summary.press("Space")
            expect(self.page.locator(".service-details[open]")).to_have_count(0)
            # Compare the reserved slot to the actual card after closing at the new width.
            self.page.wait_for_function("""()=>[...document.querySelectorAll('.service-card-slot')].every(
                slot=>Math.abs(slot.getBoundingClientRect().height-slot.querySelector('.service-card').getBoundingClientRect().height)<=1
            )""")
            summary.press("Enter")

    def test_service_accordion_smooth_motion_and_reduced_motion(self):
        self.page.emulate_media(reduced_motion="no-preference")
        self.open("services.html")
        details = self.page.locator(".service-details").first
        details.locator("summary").scroll_into_view_if_needed()
        # Read real layout on animation frames, including intermediate heights.
        sample = """async el=>{
            const samples=[el.getBoundingClientRect().height];
            el.querySelector('summary').click();
            const until=performance.now()+400;
            while(performance.now()<until){
                await new Promise(requestAnimationFrame);
                samples.push(el.getBoundingClientRect().height);
            }
            return samples;
        }"""
        opening = details.evaluate(sample)
        self.assertGreater(opening[-1], opening[0] + 100)
        self.assertTrue(any(opening[0] + 3 < value < opening[-1] - 3 for value in opening))
        closing = details.evaluate(sample)
        self.assertLess(closing[-1], closing[0] - 100)
        self.assertTrue(any(closing[-1] + 3 < value < closing[0] - 3 for value in closing))
        self.page.emulate_media(reduced_motion="reduce")
        self.assertEqual(details.evaluate("el=>getComputedStyle(el,'::details-content').transitionDuration"), "0s")
        details.locator("summary").click()
        expect(details).to_have_attribute("open", "")
        # No CSS transition remains when motion is reduced.
        self.assertEqual(details.evaluate("el=>getComputedStyle(el,'::details-content').transitionProperty"), "none")

    def test_no_javascript_fallback(self):
        plain = self.browser.new_context(java_script_enabled=False, viewport={"width": 375, "height": 1000})
        plain.route("**/*", self.local_only)
        plain.on("request", self.record_request)
        try:
            page = plain.new_page()
            page.goto(self.base + "services.html")
            expect(page.locator(".service-details")).to_have_count(6)
            page.locator(".service-details summary").first.click()
            self.assertTrue(page.locator(".service-details").first.evaluate("el=>el.open"))
            # Native keyboard navigation also works when page scripts are disabled.
            page.locator(".service-details summary").nth(1).focus()
            page.keyboard.press("Enter")
            expect(page.locator(".service-details[open]")).to_have_count(1)
            self.assertFalse(page.locator(".service-details").first.evaluate("el=>el.open"))
            page.keyboard.press("Tab")
            expect(page.locator('.service-action[href="./calculator.html?project=corporate"]')).to_be_focused()
            page.keyboard.press("Enter")
            page.wait_for_url(self.base + "calculator.html?project=corporate")
            expect(page.locator("#page-count")).to_be_disabled()
            expect(page.locator("#project-landing")).to_be_checked()
            self.assertIn("включите JavaScript", page.locator("noscript").inner_text())
            page.goto(self.base + "services.html")
            page.locator('.service-action[href="./contact.html?service=support"]').focus()
            page.keyboard.press("Enter")
            page.wait_for_url(self.base + "contact.html?service=support")
            expect(page.locator("#message")).to_have_value("")
            expect(page.get_by_role("button", name="Отправить", exact=True)).to_be_disabled()
        finally:
            plain.close()


if __name__ == "__main__":
    unittest.main()
