// Copyright (c) 2025, Zvomaita Technologies (Pvt) Ltd and contributors
// For license information, please see license.txt

function build_bins_html(data) {
	const palette = {
		good: '#10b981',
		warning: '#f59e0b',
		critical: '#ef4444',
		neutral: '#6b7280',
		blue: '#3b82f6'
	};
	
	const getUtilizationColor = (pct) => {
		if (pct === 0) return palette.neutral;
		if (pct < 50) return palette.good;
		if (pct < 70) return palette.blue;
		if (pct < 90) return palette.warning;
		return palette.critical;
	};
		
	// Helper function to format null/undefined values
	const formatValue = (value, defaultText = '—') => {
		return (value === null || value === undefined) ? defaultText : value;
	};
	
	let html = `
		<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
			<!-- Bay Summary Header - Compact -->
			<div style="background: linear-gradient(135deg, var(--primary-color, #2490ef) 0%, #1976d2 100%); color: white; padding: 16px 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
				<div style="margin-bottom: 12px; font-size: 16px; font-weight: 600; color: white;">
					Bay ${data.bay.bay_code} - ${data.bay.bay_type}
				</div>
				<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px;">
					<div>
						<div style="font-size: 11px; margin-bottom: 2px; font-weight: 500; color: white; opacity: 0.95;">Total Bins</div>
						<div style="font-size: 22px; font-weight: 600; color: white;">${formatValue(data.summary.total_bins, 0)}</div>
					</div>
					<div>
						<div style="font-size: 11px; margin-bottom: 2px; font-weight: 500; color: white; opacity: 0.95;">Occupied</div>
						<div style="font-size: 22px; font-weight: 600; color: white;">${formatValue(data.summary.occupied_bins, 0)}</div>
					</div>
					<div>
						<div style="font-size: 11px; margin-bottom: 2px; font-weight: 500; color: white; opacity: 0.95;">Available</div>
						<div style="font-size: 22px; font-weight: 600; color: white;">${formatValue(data.summary.available_bins, '—')}</div>
					</div>
					<div>
						<div style="font-size: 11px; margin-bottom: 2px; font-weight: 500; color: white; opacity: 0.95;">Avg Utilization</div>
						<div style="font-size: 22px; font-weight: 600; color: white;">${data.summary.avg_utilization ? data.summary.avg_utilization.toFixed(1) + '%' : '—'}</div>
					</div>
				</div>
			</div>
	`;		// Capacity by UOM section
		if (data.capacity_by_uom && data.capacity_by_uom.length > 0) {
			html += `
				<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
					<h3 style="margin: 0 0 16px 0; color: #1f2937; font-size: 18px; font-weight: 600;">
						📊 Capacity by Unit of Measure
					</h3>
					<div style="display: grid; gap: 12px;">
			`;
			
			data.capacity_by_uom.forEach(uom => {
				const utilization = uom.max_capacity > 0 ? (uom.used_capacity / uom.max_capacity * 100) : 0;
				const barColor = getUtilizationColor(utilization);
				
				html += `
					<div style="background: white; padding: 16px; border-radius: 8px; border-left: 4px solid ${barColor};">
						<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
							<div>
								<span style="font-weight: 700; color: #1f2937; font-size: 16px;">${uom.capacity_uom}</span>
								<span style="color: #6b7280; font-size: 13px; margin-left: 8px;">(${uom.bin_count} bins)</span>
							</div>
							<div style="font-size: 14px; font-weight: 600; color: #374151;">
								${uom.used_capacity.toFixed(1)} / ${uom.max_capacity.toFixed(1)} (${utilization.toFixed(1)}%)
							</div>
						</div>
						<div style="background: #e5e7eb; height: 10px; border-radius: 5px; overflow: hidden;">
							<div style="background: ${barColor}; height: 100%; width: ${Math.min(utilization, 100)}%; transition: width 0.3s;"></div>
						</div>
					</div>
				`;
			});
			
			html += `
					</div>
				</div>
			`;
		}
		
		// Bins Grid
		html += `
			<div style="margin-bottom: 16px;">
				<h3 style="margin: 0 0 16px 0; color: #1f2937; font-size: 18px; font-weight: 600;">
					🗺️ Bin Layout (${data.bins.length} bins)
				</h3>
				<div style="display: flex; gap: 16px; margin-bottom: 16px; font-size: 13px; color: #6b7280;">
					<span><span style="display: inline-block; width: 12px; height: 12px; background: ${palette.neutral}; border-radius: 2px; margin-right: 4px;"></span>Empty</span>
					<span><span style="display: inline-block; width: 12px; height: 12px; background: ${palette.good}; border-radius: 2px; margin-right: 4px;"></span>&lt;50%</span>
					<span><span style="display: inline-block; width: 12px; height: 12px; background: ${palette.blue}; border-radius: 2px; margin-right: 4px;"></span>50-70%</span>
					<span><span style="display: inline-block; width: 12px; height: 12px; background: ${palette.warning}; border-radius: 2px; margin-right: 4px;"></span>70-90%</span>
					<span><span style="display: inline-block; width: 12px; height: 12px; background: ${palette.critical}; border-radius: 2px; margin-right: 4px;"></span>&gt;90%</span>
				</div>
			</div>
			
			<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px;">
		`;
		
		// Individual bin cards
		data.bins.forEach(bin => {
			const color = getUtilizationColor(bin.capacity_utilization_pct);
			const statusEmoji = bin.capacity_utilization_pct === 0 ? '⚪' : 
								bin.capacity_utilization_pct < 50 ? '🟢' :
								bin.capacity_utilization_pct < 70 ? '🔵' :
								bin.capacity_utilization_pct < 90 ? '🟠' : '🔴';
			
			html += `
				<div style="
					background: white;
					border: 2px solid ${color};
					border-radius: 10px;
					padding: 16px;
					cursor: pointer;
					transition: all 0.2s;
					box-shadow: 0 2px 4px rgba(0,0,0,0.05);
				" onclick="frappe.set_route('Form', 'Warehouse Bin', '${bin.bin_code}')"
				   onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.15)';"
				   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)';">
					
					<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
						<div>
							<div style="font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 4px;">
								${bin.bin_code}
							</div>
							<div style="font-size: 12px; color: #6b7280;">
								${bin.bin_type}
							</div>
						</div>
						<div style="font-size: 24px;">
							${statusEmoji}
						</div>
					</div>
					
					${bin.max_capacity > 0 ? `
						<div style="background: #f9fafb; border-radius: 6px; padding: 10px; margin-bottom: 10px;">
							<div style="font-size: 11px; color: #6b7280; margin-bottom: 4px; text-transform: uppercase;">
								Capacity (${bin.capacity_uom})
							</div>
							<div style="font-size: 18px; font-weight: 700; color: #1f2937;">
								${bin.current_capacity_used.toFixed(1)} / ${bin.max_capacity.toFixed(1)}
							</div>
							<div style="font-size: 12px; color: #6b7280; margin-top: 2px;">
								${bin.capacity_utilization_pct.toFixed(1)}% utilized
							</div>
						</div>
						
						<div style="background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden;">
							<div style="background: ${color}; height: 100%; width: ${Math.min(bin.capacity_utilization_pct, 100)}%; transition: width 0.3s;"></div>
						</div>
					` : `
						<div style="text-align: center; padding: 16px; color: #9ca3af; font-size: 12px; background: #f9fafb; border-radius: 6px;">
							⚠️ No capacity limits
						</div>
					`}
					
					${bin.max_weight_kg ? `
						<div style="font-size: 11px; color: #6b7280; margin-top: 8px; text-align: center;">
							Max Weight: ${bin.max_weight_kg} kg
						</div>
					` : ''}
				</div>
			`;
		});
	
	html += `
		</div>
	</div>
	`;
	
	return html;
}

frappe.ui.form.on('Warehouse Bay', {
	refresh: function(frm) {
		// Only render bins if bay is saved and has a bay_code
		if (!frm.is_new() && frm.doc.bay_code) {
			frm.trigger('render_bins_html');
			
			// Add Create Bin button as primary action
			frm.add_custom_button(__('Create Bin'), function() {
				frappe.new_doc('Warehouse Bin', {
					bay: frm.doc.bay_code,
					bay_type: frm.doc.bay_type
				});
			}).css({'background-color': 'var(--primary-color)', 'color': 'white', 'font-weight': '500'});
			
			// Add refresh button as standalone
			frm.add_custom_button(__('Refresh Bins'), function() {
				frm.trigger('render_bins_html');
			});
		} else {
			// Show placeholder message for new bays
			frm.fields_dict.notes.$wrapper.html(`
				<div style="padding: 40px; text-align: center; color: #6b7280; background: #f9fafb; border-radius: 8px;">
					<div style="font-size: 18px; margin-bottom: 8px;">📦</div>
					<div style="font-size: 14px; font-weight: 500;">Save this bay first to see bin layout</div>
					<div style="font-size: 12px; margin-top: 4px;">Bins will be displayed here after you save and create bins for this bay</div>
				</div>
			`);
		}
	},
	
	render_bins_html: function(frm) {
		if (!frm.doc.bay_code) {
			frappe.msgprint(__('Please save the bay first'));
			return;
		}
		
		frappe.call({
			method: 'freightmas.warehouse_service.doctype.warehouse_bay.warehouse_bay.get_bay_with_bins',
			args: { bay_code: frm.doc.bay_code },
			callback: function(r) {
				if (r.message) {
					let html = build_bins_html(r.message);
					// Set HTML content directly to the field wrapper
					frm.fields_dict.notes.$wrapper.html(html);
				}
			}
		});
	}
});
