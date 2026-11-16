"""Automatic service scrolling: real viewport positions, cancellation and motion settings."""
import unittest
from playwright.sync_api import expect
import test_service_flow as flow


class ServiceScrollTests(unittest.TestCase):
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

    def arrange_near_bottom(self, index):
        summary = self.page.locator('.service-details summary').nth(index)
        summary.focus()
        summary.evaluate('''el=>scrollTo({
            top:Math.max(0,scrollY+el.getBoundingClientRect().top-innerHeight+150),behavior:'instant'
        })''')
        return summary

    def spy_scroll(self):
        self.page.evaluate('''()=>{
            window.serviceScrollCalls=[];
            const real=window.scrollTo.bind(window);
            window.scrollTo=(...args)=>{serviceScrollCalls.push(args[0]);return real(...args);};
        }''')

    def wait_aligned(self, index):
        self.page.wait_for_function('''index=>{
            const details=document.querySelectorAll('.service-details')[index];
            const card=details.closest('.service-card').getBoundingClientRect();
            const safeTop=document.querySelector('.site-header').getBoundingClientRect().bottom+16;
            const available=innerHeight-16-safeTop;
            if(card.height<=available) return Math.abs((card.top+card.bottom)/2-(safeTop+innerHeight-16)/2)<4;
            return Math.abs(details.querySelector('summary').getBoundingClientRect().top-safeTop)<4;
        }''', arg=index)

    def test_open_scrolls_to_description_without_shifting_grid(self):
        for width in (375, 768, 1024, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.open('services.html')
                summary = self.arrange_near_bottom(3)
                before_y = self.page.evaluate('scrollY')
                positions = '''grid=>[...grid.querySelectorAll('.service-card-slot')].map(el=>
                    el.getBoundingClientRect().top-grid.getBoundingClientRect().top)'''
                grid = self.page.locator('.services-grid')
                before = grid.evaluate(positions)
                summary.click()
                self.wait_aligned(3)
                self.assertGreater(self.page.evaluate('scrollY'), before_y)
                expect(summary).to_be_focused()
                expect(self.page.locator('.service-details[open]')).to_have_count(1)
                for a, b in zip(before, grid.evaluate(positions)):
                    self.assertAlmostEqual(a, b, delta=1)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

    def test_visible_card_centers_and_reopening_does_not_scroll(self):
        for width in (375, 768, 1024, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 1800})
                self.open('services.html')
                summary = self.page.locator('.service-details summary').first
                summary.focus()
                summary.evaluate('''el=>{
                    const top=document.querySelector('.site-header').getBoundingClientRect().bottom+48;
                    scrollTo({top:scrollY+el.getBoundingClientRect().top-top,behavior:'instant'});
                }''')
                self.spy_scroll()
                summary.press('Enter')
                self.wait_aligned(0)
                self.assertEqual(len(self.page.evaluate('serviceScrollCalls')), 1)
                # At this height the whole card fits: verify actual center and column.
                card = self.page.locator('.service-card').first
                geometry = card.evaluate('''el=>{
                    const r=el.getBoundingClientRect();
                    const slot=el.parentElement.getBoundingClientRect();
                    const safeTop=document.querySelector('.site-header').getBoundingClientRect().bottom+16;
                    return {center:(r.top+r.bottom)/2,target:(safeTop+innerHeight-16)/2,
                        top:r.top,bottom:r.bottom,safeTop,left:r.left,slotLeft:slot.left};
                }''')
                self.assertAlmostEqual(geometry['center'], geometry['target'], delta=2)
                self.assertAlmostEqual(geometry['left'], geometry['slotLeft'], delta=1)
                self.assertGreaterEqual(geometry['top'], geometry['safeTop'])
                self.assertLessEqual(geometry['bottom'], 1784)
                before = self.page.evaluate('scrollY')
                summary.press('Space')
                self.page.wait_for_timeout(100)
                self.spy_scroll()
                summary.press('Space')
                self.wait_aligned(0)
                self.page.wait_for_timeout(100)
                self.assertEqual(self.page.evaluate('serviceScrollCalls'), [])
                self.assertAlmostEqual(before, self.page.evaluate('scrollY'), delta=1)
                expect(summary).to_be_focused()

    def test_cancellation_and_latest_open_card(self):
        self.page.emulate_media(reduced_motion='no-preference')
        for action in ('close', 'wheel', 'touchmove', 'PageDown'):
            with self.subTest(action=action):
                self.open('services.html')
                summary = self.arrange_near_bottom(3)
                self.spy_scroll()
                summary.evaluate('el=>el.click()')
                self.page.wait_for_function("document.querySelectorAll('.service-card-slot')[3].classList.contains('is-expanded')")
                if action == 'close':
                    summary.evaluate('el=>el.click()')
                elif action == 'PageDown':
                    self.page.keyboard.press('PageDown')
                else:
                    self.page.evaluate('name=>window.dispatchEvent(new Event(name))', action)
                self.page.wait_for_timeout(350)
                self.assertEqual(self.page.evaluate('serviceScrollCalls'), [])
        self.open('services.html')
        self.arrange_near_bottom(4)
        self.spy_scroll()
        self.page.evaluate('''async ()=>{
            const summaries=document.querySelectorAll('.service-details summary');
            summaries[0].click();
            await new Promise(resolve=>setTimeout(resolve,50));
            summaries[4].click();
        }''')
        self.wait_aligned(4)
        self.assertTrue(self.page.locator('.service-details').nth(4).evaluate('el=>el.open'))
        self.assertEqual(len(self.page.evaluate('serviceScrollCalls')), 1)

    def test_smooth_and_reduced_motion_scroll_keep_focus(self):
        for preference, behavior in (('no-preference', 'smooth'), ('reduce', 'auto')):
            with self.subTest(preference=preference):
                self.page.emulate_media(reduced_motion=preference)
                self.open('services.html')
                summary = self.arrange_near_bottom(3)
                self.spy_scroll()
                summary.press('Enter')
                self.wait_aligned(3)
                calls = self.page.evaluate('serviceScrollCalls')
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0]['behavior'], behavior)
                expect(summary).to_be_focused()
