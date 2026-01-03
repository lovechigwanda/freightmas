// Copyright (c) 2025, Navari Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Bin', {
	refresh: function(frm) {
		// Load and display current allocations
		if (!frm.is_new()) {
			load_current_allocations(frm);
		}
	}
});

function load_current_allocations(frm) {
	frappe.call({
		method: 'get_current_allocations',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				render_allocations_html(frm, r.message);
			}
		}
	});
}

function render_allocations_html(frm, allocations) {
	let html = '';
	
	if (!allocations || allocations.length === 0) {
		html = `
			<div style="padding: 20px; text-align: center; color: #888; background: #f9f9f9; border-radius: 4px;">
				<div style="font-size: 48px; margin-bottom: 10px;">📦</div>
				<div style="font-size: 16px; font-weight: 500;">No Current Allocations</div>
				<div style="font-size: 14px; margin-top: 5px;">This bin is currently empty</div>
			</div>
		`;
	} else {
		// Calculate totals
		let total_qty = allocations.reduce((sum, a) => sum + a.quantity_remaining, 0);
		let total_weight = allocations.reduce((sum, a) => sum + (a.weight_kg || 0), 0);
		let total_capacity = allocations.reduce((sum, a) => sum + (a.capacity_used || 0), 0);
		
		// Capacity status with bin's UOM
		let capacity_html = '';
		if (frm.doc.uom && frm.doc.max_capacity) {
			let capacity_pct = frm.doc.capacity_utilization_pct || 0;
			let status_color = capacity_pct > 90 ? '#d32f2f' : (capacity_pct > 70 ? '#f57c00' : '#388e3c');
			let status_icon = capacity_pct > 90 ? '🔴' : (capacity_pct > 70 ? '🟠' : '🟢');
			
			capacity_html = `
				<div style="margin-bottom: 15px; padding: 12px; background: #f5f5f5; border-radius: 4px;">
					<div style="display: flex; justify-content: space-between; align-items: center;">
						<div>
							<span style="font-size: 14px; color: #666;">Capacity (${frm.doc.uom}):</span>
							<strong style="font-size: 16px; color: ${status_color}; margin-left: 8px;">
								${status_icon} ${total_capacity.toFixed(2)} / ${frm.doc.max_capacity} (${capacity_pct.toFixed(1)}%)
							</strong>
						</div>
						<div style="display: flex; gap: 20px;">
							<div style="font-size: 14px; color: #666;">
								Units: <strong>${total_qty}</strong>
							</div>
							<div style="font-size: 14px; color: #666;">
								Weight: <strong>${total_weight.toFixed(2)} kg</strong>
							</div>
						</div>
					</div>
				</div>
			`;
		} else {
			// Fallback if no capacity limits set
			capacity_html = `
				<div style="margin-bottom: 15px; padding: 12px; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107;">
					<div style="display: flex; justify-content: space-between; align-items: center;">
						<div style="color: #856404;">
							⚠️ No capacity limits configured for this bin
						</div>
						<div style="display: flex; gap: 20px;">
							<div style="font-size: 14px; color: #666;">
								Units: <strong>${total_qty}</strong>
							</div>
							<div style="font-size: 14px; color: #666;">
								Weight: <strong>${total_weight.toFixed(2)} kg</strong>
							</div>
						</div>
					</div>
				</div>
			`;
		}
		
		// Allocation cards
		html = capacity_html;
		
		allocations.forEach(function(allocation) {
			let days_badge_color = allocation.days_stored > 90 ? '#d32f2f' : 
			                        (allocation.days_stored > 30 ? '#f57c00' : '#388e3c');
			
			// Build capacity info based on bin's UOM
			let capacity_info = '';
			if (frm.doc.uom && allocation.capacity_used) {
				capacity_info = `<span style="color: #666; margin-left: 4px;">≈ ${allocation.capacity_used.toFixed(2)} ${frm.doc.uom}</span>`;
			}
			
			html += `
				<div style="margin-bottom: 12px; padding: 14px; border: 1px solid #e0e0e0; border-radius: 4px; background: white;">
					<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
						<div style="flex: 1;">
							<div style="font-size: 14px; font-weight: 600; color: #333; margin-bottom: 4px;">
								<a href="/app/customer-goods-receipt/${allocation.goods_receipt}" style="text-decoration: none;">
									📥 ${allocation.goods_receipt}
								</a>
							</div>
							<div style="font-size: 13px; color: #666; margin-bottom: 3px;">
								<strong>${allocation.customer}</strong>
							</div>
							<div style="font-size: 13px; color: #888;">
								${allocation.customer_reference || 'N/A'} • ${allocation.description}
							</div>
						</div>
						<div style="text-align: right;">
							<span style="display: inline-block; padding: 4px 10px; background: ${days_badge_color}; color: white; border-radius: 12px; font-size: 12px; font-weight: 500;">
								${allocation.days_stored} days
							</span>
						</div>
					</div>
					<div style="display: flex; gap: 20px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f0f0f0; font-size: 13px;">
						<div>
							<span style="color: #888;">Qty:</span> 
							<strong style="color: #333;">${allocation.quantity_remaining} / ${allocation.original_qty}</strong>
							<span style="color: #666; margin-left: 4px;">${allocation.storage_unit_type}</span>
							${capacity_info}
						</div>
						<div>
							<span style="color: #888;">Weight:</span> 
							<strong style="color: #333;">${(allocation.weight_kg || 0).toFixed(2)} kg</strong>
						</div>
						<div>
							<span style="color: #888;">Since:</span> 
							<strong style="color: #333;">${frappe.datetime.str_to_user(allocation.receipt_date)}</strong>
						</div>
					</div>
				</div>
			`;
		});
	}
	
	frm.fields_dict.current_allocations_html.$wrapper.html(html);
}
