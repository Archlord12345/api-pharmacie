import unittest

import app
from app import apply_filters, parse_guard_pharmacies


class ParseGuardPharmaciesTests(unittest.TestCase):
    def test_parse_table_rows(self) -> None:
        sample_html = """
        <table>
            <tr><th>Nom</th><th>Adresse</th><th>Téléphone</th></tr>
            <tr><td>Pharmacie Bastos</td><td>Yaoundé</td><td>+237 699 00 00 00</td></tr>
            <tr><td>Pharmacie Bonapriso</td><td>Douala</td><td>+237 677 11 22 33</td></tr>
        </table>
        """

        result = parse_guard_pharmacies(sample_html)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[1]["name"], "Pharmacie Bastos")
        self.assertEqual(result[1]["phone"], "+237 699 00 00 00")

    def test_parse_list_items_fallback(self) -> None:
        sample_html = """
        <ul>
            <li>Pharmacie Elig-Essono - Yaoundé - +237 690001122</li>
            <li>Clinique Centrale</li>
        </ul>
        """

        result = parse_guard_pharmacies(sample_html)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Pharmacie Elig")


class ApplyFiltersTests(unittest.TestCase):
    def test_filter_by_city_and_region(self) -> None:
        pharmacies = [
            {
                "name": "Pharmacie Bastos",
                "address": "Carrefour Bastos",
                "city": "Yaoundé",
                "region": "Centre",
                "phone": "+237 600000000",
                "details": "Pharmacie Bastos Yaoundé Centre",
            },
            {
                "name": "Pharmacie Akwa",
                "address": "Rue Joffre",
                "city": "Douala",
                "region": "Littoral",
                "phone": "+237 611111111",
                "details": "Pharmacie Akwa Douala Littoral",
            },
        ]

        result = apply_filters(pharmacies, ville="yaounde", region="centre")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Pharmacie Bastos")


class ApiFiltersTests(unittest.TestCase):
    def setUp(self) -> None:
        app.fetch_guard_pharmacies = lambda: [
            {
                "name": "Pharmacie Bastos",
                "address": "Carrefour Bastos",
                "city": "Yaoundé",
                "region": "Centre",
                "phone": "+237 600000000",
                "details": "Pharmacie Bastos Yaoundé Centre",
            },
            {
                "name": "Pharmacie Akwa",
                "address": "Rue Joffre",
                "city": "Douala",
                "region": "Littoral",
                "phone": "+237 611111111",
                "details": "Pharmacie Akwa Douala Littoral",
            },
        ]

    def test_list_guard_pharmacies_with_known_filters(self) -> None:
        result = app.list_guard_pharmacies(ville="yaounde", region="centre", autour=None)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["filters"]["ville"], "Yaoundé")
        self.assertEqual(result["filters"]["region"], "Centre")
        self.assertIn("Yaoundé", result["available_filters"]["villes"])
        self.assertIn("Centre", result["available_filters"]["regions"])

    def test_list_guard_pharmacies_with_unknown_region(self) -> None:
        with self.assertRaises(app.HTTPException) as context:
            app.list_guard_pharmacies(ville=None, region="RegionX", autour=None)

        self.assertEqual(context.exception.status_code, 400)

    def test_list_available_filters(self) -> None:
        result = app.list_available_filters()

        self.assertIn("Yaoundé", result["villes"])
        self.assertIn("Centre", result["regions"])


if __name__ == "__main__":
    unittest.main()
