// Copyright (c) 2025, Tanmoy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Drift Test Definition", {
    refresh(frm) {
        [
            ["Test Now", "create_test"]
        ].forEach(([label, method]) => {
            frm.add_custom_button(label, () => frm.call(method));
        });
	},
});
