// Copyright (c) 2025, Tanmoy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Drift Test", {
    refresh(frm) {
        [
            ["Execute", "next", frm.doc.status === "Pending" || frm.doc.status === "Stopped"],
        ].forEach(([label, action, condition]) => {
            if (condition) {
                frm.add_custom_button(label, () => frm.call(action));
            }
        });
	},
});
