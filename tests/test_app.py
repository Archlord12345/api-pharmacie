import unittest

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


if __name__ == "__main__":
    unittest.main()
