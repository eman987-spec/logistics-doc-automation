import unittest

from scripts.evidence_locations import compute_pdf_locations, match_value_in_text, value_variants


class EvidenceValueMatchingTests(unittest.TestCase):
    def test_number_variants_cover_invoice_print_formats(self):
        examples = {
            "3578112": "3,578,112.00",
            "91226": "91,226.00",
            "14605": "14,605.000000",
            "3669338": "3,669,338.00",
        }
        for value, printed in examples.items():
            with self.subTest(value=value):
                variants = value_variants(value)
                self.assertIn(printed, variants)
                self.assertIsNotNone(match_value_in_text(printed, value))

    def test_date_variants_cover_day_month_year(self):
        variants = value_variants("2022-01-04")
        self.assertIn("04-JAN-2022", variants)
        self.assertIsNotNone(match_value_in_text("Invoice date 04-JAN-2022", "2022-01-04"))

    def test_short_decimal_does_not_match_inside_longer_amount(self):
        self.assertIsNone(match_value_in_text("189.60", "89.6"))
        self.assertIsNotNone(match_value_in_text("Amount 89.60", "89.6"))

    def test_pdf_locations_use_document_page_and_nearby_labels(self):
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        document = fitz.open()
        document.new_page(width=612, height=792)
        page = document.new_page(width=612, height=792)
        page.insert_text((50, 100), "Total excluding tax: 3,578,112.00")
        page.insert_text((50, 150), "Amount due: 3,578,112.00")
        description = "This description wraps across multiple lines"
        page.insert_textbox(fitz.Rect(50, 200, 145, 260), description, fontsize=10)

        locations = compute_pdf_locations(
            document.tobytes(),
            {
                "header": {"SUBTOTALAMOUNT": "3578112"},
                "invoiceHeader": {
                    "SUBTOTALAMOUNT": "3578112",
                    "TOTALAMOUNTDUE": "3578112",
                    "description": description,
                }
            },
            page_start=2,
            page_end=2,
        )

        subtotal = locations["invoiceHeader.SUBTOTALAMOUNT"]
        total = locations["invoiceHeader.TOTALAMOUNTDUE"]
        self.assertEqual(subtotal["page"], 2)
        self.assertEqual(total["page"], 2)
        self.assertNotEqual(subtotal["rects"], total["rects"])
        self.assertGreater(len(locations["invoiceHeader.description"]["rects"]), 1)
        for location in (subtotal, total):
            self.assertTrue(all(0 <= coordinate <= 1 for coordinate in location["rects"][0]))


if __name__ == "__main__":
    unittest.main()
