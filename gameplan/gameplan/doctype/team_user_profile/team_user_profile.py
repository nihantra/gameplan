# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
import gameplan
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.website.utils import cleanup_page_name
from gameplan.gameplan.doctype.team_user_profile.profile_photo import remove_background


class TeamUserProfile(Document):
	def autoname(self):
		self.name = self.generate_name()

	def generate_name(self):
		full_name = frappe.db.get_value("User", self.user, "full_name")
		return append_number_if_name_exists(self.doctype, cleanup_page_name(full_name))

	@frappe.whitelist()
	def set_image(self, image):
		self.image = image
		self.is_image_background_removed = False
		self.image_background_color = None
		self.original_image = None
		self.save()
		gameplan.refetch_resource('Users')

	@frappe.whitelist()
	def remove_image_background(self, default_color=None):
		if not self.image:
			frappe.throw('Profile image not found')
		file = frappe.get_doc('File', {'file_url': self.image })
		self.original_image = file.file_url
		image_content = remove_background(file)
		filename, extn = file.get_extension()
		output_filename = f'{filename}_no_bg.png'
		new_file = frappe.get_doc(
			doctype="File",
			file_name=output_filename,
			content=image_content,
			is_private=0,
			attached_to_doctype=self.doctype,
			attached_to_name=self.name
		).insert()
		self.image = new_file.file_url
		self.is_image_background_removed = True
		self.image_background_color = default_color
		self.save()
		gameplan.refetch_resource('Users')

	@frappe.whitelist()
	def revert_image_background(self):
		if self.original_image:
			self.image = self.original_image
			self.original_image = None
			self.is_image_background_removed = False
			self.image_background_color = None
			self.save()
			gameplan.refetch_resource('Users')


def create_user_profile(doc, method=None):
	if not frappe.db.exists("Team User Profile", {"user": doc.name}):
		frappe.get_doc(doctype="Team User Profile", user=doc.name).insert(ignore_permissions=True)
		frappe.db.commit()

def delete_user_profile(doc, method=None):
	exists = frappe.db.exists("Team User Profile", {"user": doc.name})
	if exists:
		return frappe.get_doc("Team User Profile", {"user": doc.name}).delete()

def on_user_update(doc, method=None):
	create_user_profile(doc)
	if any(doc.has_value_changed(field) for field in ["full_name", "enabled"]):
		print('fullname, enalbed changed, updating profile')
		profile = frappe.get_doc("Team User Profile", {"user": doc.name})
		profile.enabled = doc.enabled
		profile.full_name = doc.full_name
		profile.save(ignore_permissions=True)
