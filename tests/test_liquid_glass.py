"""Liquid Glass regression checks; reuses the local, submission-blocking fixture."""
import re
import unittest

from playwright.sync_api import expect
import test_service_flow as flow


def rgb(value):
    numbers = [float(n) for n in re.findall(r"[\d.]+", value)]
    return numbers[:3] + ([numbers[3]] if len(numbers) > 3 else [1.0])


def over(front, back):
    return [front[i] * front[3] + back[i] * (1 - front[3]) for i in range(3)]


def contrast(first, second):
    def luminance(color):
        channels = [c / 255 for c in color[:3]]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(first), luminance(second)))
    return (b + .05) / (a + .05)


class LiquidGlassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        flow.ServiceFlowTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        flow.ServiceFlowTests.tearDownClass()

    def setUp(self):
        self.fixture = flow.ServiceFlowTests('test_no_javascript_fallback')
        self.fixture.setUp()
        self.page = self.fixture.page
        self.open = self.fixture.open

    def tearDown(self):
        self.fixture.tearDown()

    def test_all_pages_reflow_and_progressive_navigation(self):
        files = sorted(flow.ROOT.glob('*.html')) + sorted((flow.ROOT / 'articles').glob('*.html'))
        for width in (320, 375, 390, 430, 768, 1024, 1440):
            self.page.set_viewport_size({'width': width, 'height': 1000})
            for file in files:
                with self.subTest(page=file.name, width=width):
                    self.open(str(file.relative_to(flow.ROOT)))
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                    expect(self.page.locator('h1')).to_have_count(1)
                    expect(self.page.locator('.header-inner.glass-panel')).to_be_visible()
                    expect(self.page.locator('#main-nav a[aria-current]')).to_have_count(1)
                    self.assertEqual(self.page.locator('.menu-toggle').is_visible(), width <= 1024)
        # Equivalent 200% desktop reflow: half-size CSS viewport with 2x pixel density.
        zoom = flow.ServiceFlowTests.browser.new_context(
            viewport={'width': 720, 'height': 500}, device_scale_factor=2, reduced_motion='reduce'
        )
        zoom.route('**/*', self.fixture.local_only)
        try:
            page = zoom.new_page()
            for file in ('index.html', 'contact.html', 'calculator.html'):
                page.goto(flow.ServiceFlowTests.base + file)
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                expect(page.locator('.menu-toggle')).to_be_visible()
        finally:
            zoom.close()
        plain = flow.ServiceFlowTests.browser.new_context(java_script_enabled=False,
                    viewport={'width': 375, 'height': 1000})
        plain.route('**/*', self.fixture.local_only)
        try:
            page = plain.new_page()
            for file in files:
                page.goto(flow.ServiceFlowTests.base + str(file.relative_to(flow.ROOT)))
                expect(page.locator('#main-nav a:visible')).to_have_count(7)
                expect(page.locator('h1')).to_be_visible()
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                if file.name == 'blog.html':
                    expect(page.locator('[data-blog-category]:visible')).to_have_count(3)
        finally:
            plain.close()

    def test_text_contrast_and_control_alignment(self):
        self.open('index.html')
        button = self.page.locator('.hero .button-dark')
        colors = button.evaluate('el=>({color:getComputedStyle(el).color,bg:getComputedStyle(el).backgroundColor})')
        self.assertGreaterEqual(contrast(rgb(colors['color']), rgb(colors['bg'])), 4.5)
        self.open('contact.html')
        panel = self.page.locator('.form-panel')
        surface = rgb(panel.evaluate('el=>getComputedStyle(el).backgroundColor'))
        muted = rgb(self.page.locator('.form-note').evaluate('el=>getComputedStyle(el).color'))
        # Dense reading surfaces must remain readable even over very dark material.
        self.assertGreaterEqual(contrast(muted, over(surface, [0, 0, 0])), 4.5)
        field = self.page.locator('#email')
        field_bg = over(rgb(field.evaluate('el=>getComputedStyle(el).backgroundColor')), [255, 253, 249])
        line = rgb(field.evaluate('el=>getComputedStyle(el).borderTopColor'))
        self.assertGreaterEqual(contrast(line, field_bg), 3)
        field.focus()
        focus = rgb(field.evaluate('el=>getComputedStyle(el).outlineColor'))
        self.assertGreaterEqual(contrast(focus, field_bg), 3)
        self.open('services.html')
        card = self.page.locator('.service-card').first
        face = rgb(card.evaluate('el=>getComputedStyle(el).backgroundColor'))
        copy = rgb(card.locator('p').first.evaluate('el=>getComputedStyle(el).color'))
        self.assertGreaterEqual(contrast(copy, over(face, [195, 101, 65])), 4.5)
        self.open('calculator.html')
        # The native circle/checkbox stays aligned with the label, not a text-input minimum height.
        for selector in ('.project-option', '.calculator-extra'):
            aligned = self.page.locator(selector).first.evaluate('''el=>{
                const input=el.querySelector('input').getBoundingClientRect();
                const label=el.querySelector('strong').getBoundingClientRect();
                return input.y+input.height/2>=label.y && input.y+input.height/2<=label.bottom;
            }''')
            self.assertTrue(aligned, selector)

    def test_dense_fallback_when_blur_enhancement_is_unavailable(self):
        css = (flow.ROOT / 'styles.css').read_text()
        guard = '@supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))'
        self.assertEqual(css.count(guard), 1)
        fallback = css.replace(guard, '@supports (unavailable-glass-enhancement: yes)')
        self.page.route('**/styles.css*', lambda route: route.fulfill(
            status=200, content_type='text/css; charset=utf-8', body=fallback
        ))
        for name in ('index.html', 'services.html', 'contact.html', 'articles/choosing-website.html'):
            self.open(name)
            for panel in self.page.locator('.glass-panel').all():
                alpha = rgb(panel.evaluate('el=>getComputedStyle(el).backgroundColor'))[3]
                self.assertGreaterEqual(alpha, .94, name)
                self.assertEqual(panel.evaluate('el=>getComputedStyle(el).backdropFilter'), 'none')
            expect(self.page.locator('h1')).to_be_visible()
        self.page.set_viewport_size({'width': 375, 'height': 900})
        self.open('index.html')
        self.page.locator('.menu-toggle').click()
        expect(self.page.locator('#main-nav a:visible')).to_have_count(7)

    def test_reduced_motion_and_missing_reveal_apis(self):
        self.page.add_init_script('window.IntersectionObserver=undefined; Element.prototype.animate=undefined;')
        self.open('index.html')
        self.page.locator('.cta-panel').scroll_into_view_if_needed()
        self.assertEqual(self.page.locator('.cta-panel').evaluate('el=>getComputedStyle(el).opacity'), '1')
        self.page.set_viewport_size({'width': 375, 'height': 900})
        self.page.locator('.menu-toggle').click()
        self.assertEqual(self.page.locator('#main-nav').evaluate('el=>getComputedStyle(el).animationName'), 'none')
        self.open('calculator.html?project=corporate')
        self.page.get_by_role('button', name='На страницу вперёд', exact=True).click()
        expect(self.page.locator('#page-count')).to_have_value('2')
        expect(self.page.locator('.book-spread')).to_have_attribute('data-book-page', '2')
        self.open('services.html')
        details = self.page.locator('.service-details').first
        details.locator('summary').click()
        self.assertEqual(details.evaluate("el=>getComputedStyle(el,'::details-content').transitionDuration"), '0s')

    def test_floating_header_anchors_and_short_landscape_menu(self):
        for width in (375, 768, 1440):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.open('articles/choosing-website.html')
            self.page.locator('nav[aria-label="Содержание статьи"] a').first.click()
            heading = self.page.locator('#start').bounding_box()
            header = self.page.locator('.header-inner').bounding_box()
            self.assertGreaterEqual(heading['y'], header['y'] + header['height'])
        self.page.set_viewport_size({'width': 375, 'height': 420})
        self.open('index.html')
        menu = self.page.locator('.menu-toggle')
        menu.click()
        self.page.keyboard.press('Tab')
        first = self.page.locator('#main-nav a').first
        expect(first).to_be_focused()
        ring_fits = first.evaluate('''el=>{
            const box=el.getBoundingClientRect(),nav=el.closest('nav').getBoundingClientRect(),style=getComputedStyle(el);
            const ring=parseFloat(style.outlineWidth)+parseFloat(style.outlineOffset);
            return box.left-ring>=nav.left-.5 && box.right+ring<=nav.right+.5;
        }''')
        self.assertTrue(ring_fits, 'Keyboard outline must fit inside the scrolling menu')
        last = self.page.locator('#main-nav a').last
        last.scroll_into_view_if_needed()
        box = last.bounding_box()
        self.assertGreaterEqual(box['y'], 0)
        self.assertLessEqual(box['y'] + box['height'], 420)
        self.page.keyboard.press('Escape')
        expect(menu).to_have_attribute('aria-expanded', 'false')
        expect(menu).to_be_focused()
