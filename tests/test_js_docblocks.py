import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docblock2web.main import DocBlock2Web


class DocBlockJsParsingTest(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		sample_path = Path(__file__).resolve().parents[1] / "sample.js"
		with sample_path.open("r", encoding="utf-8") as handle:
			cls.docblocks = DocBlock2Web(handle).dockblocks

	def _by_name(self, target):
		for db in self.docblocks:
			if getattr(db, "name", None) == target:
				return db
		raise AssertionError(f"Docblock with name '{target}' not found")

	def test_top_level_functions_promoted(self):
		add_block = self._by_name("add")
		double_block = self._by_name("double")
		self.assertEqual(add_block.type, "js_function")
		self.assertEqual(double_block.type, "js_function")
		self.assertTrue(add_block.tokens.get("param"))
		self.assertTrue(double_block.tokens.get("param"))

	def test_class_assets_detected(self):
		greeter = self._by_name("Greeter")
		self.assertEqual(greeter.type, "class")
		public_methods = [db.name for db in greeter.assets["methods"]["public"]]
		static_methods = [db.name for db in greeter.assets["methods"]["static"]]
		properties = [db.name for db in greeter.assets["properties"]["public"]]

		self.assertIn("constructor", public_methods)
		self.assertIn("greet", public_methods)
		self.assertIn("shout", static_methods)
		self.assertIn("name", properties)

	def test_jquery_plugin_structure(self):
		plugin = self._by_name("myPlugin")
		self.assertEqual(plugin.type, "jquery_plugin")

		public_methods = [db.name for db in plugin.assets["methods"]["public"]]
		self.assertIn("init", public_methods)
		self.assertIn("a_method", public_methods)

		static_properties = [db.name for db in plugin.assets["properties"]["static"]]
		public_properties = [db.name for db in plugin.assets["properties"]["public"]]

		self.assertIn("myPlugin.defaults", static_properties)
		self.assertIn("settings", public_properties)


if __name__ == '__main__':
	unittest.main()
