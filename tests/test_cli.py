"""CLI behavior tests for the NLAlpha bundle."""

from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from nlalpha.cli import doctor, main, serve


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_distributions_and_entry_points(self):
        entries = [SimpleNamespace(name="cta")]
        with patch.object(doctor, "version", return_value="1.0.0"), \
                patch.object(doctor, "entry_points", return_value=entries):
            self.assertEqual(doctor.run_doctor(None), 0)

    def test_doctor_reports_missing_distribution(self):
        with patch.object(doctor, "version", side_effect=PackageNotFoundError), \
                patch.object(doctor, "entry_points", return_value=[SimpleNamespace(name="cta")]):
            self.assertEqual(doctor.run_doctor(None), 1)

    def test_doctor_reports_empty_entry_point_group(self):
        with patch.object(doctor, "version", return_value="1.0.0"), \
                patch.object(doctor, "entry_points", return_value=[]):
            self.assertEqual(doctor.run_doctor(None), 1)


class ServeTests(unittest.TestCase):
    def test_serve_imports_selected_service_and_runs_main(self):
        module = SimpleNamespace(main=Mock())
        with patch.object(serve, "import_module", return_value=module) as importer:
            self.assertEqual(serve.run_serve(SimpleNamespace(service="data")), 0)
        importer.assert_called_once_with("nlalpha_data.server")
        module.main.assert_called_once_with()


class MainTests(unittest.TestCase):
    def test_main_dispatches_doctor_and_serve(self):
        with patch.object(main, "run_doctor", return_value=7) as doctor_handler:
            self.assertEqual(main.main(["doctor"]), 7)
        doctor_handler.assert_called_once()
        with patch.object(main, "run_serve", return_value=8) as serve_handler:
            self.assertEqual(main.main(["serve", "capability"]), 8)
        self.assertEqual(serve_handler.call_args.args[0].service, "capability")

    def test_main_requires_a_subcommand(self):
        with self.assertRaises(SystemExit):
            main.main([])
