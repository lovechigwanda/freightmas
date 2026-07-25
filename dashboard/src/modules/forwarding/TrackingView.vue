<template>
	<div>
		<div class="sd-card">
			<div class="sd-card-title" style="margin-bottom: 14px;">
				<span class="sd-card-title-main">Tracking Reports</span>
			</div>

			<div class="tr-table">
				<div class="tr-row">
					<div class="tr-name">Full Tracking Report</div>
					<div class="tr-filter">
						<CustomerFilterDropdown v-model="selectedCustomers" />
					</div>
					<div class="tr-action">
						<a class="sd-btn sd-btn-primary" :href="trackingReportHref" target="_blank" rel="noopener">
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</a>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Simplified Tracking Report <span class="tr-soon">Soon</span>
					</div>
					<div class="tr-filter">
						<button type="button" class="cfd-trigger" disabled>Select Customers</button>
					</div>
					<div class="tr-action">
						<button type="button" class="sd-btn sd-btn-primary" disabled>
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</button>
					</div>
				</div>

				<div class="tr-row">
					<div class="tr-name">
						Per Job Tracking Report <span class="tr-soon">Soon</span>
					</div>
					<div class="tr-filter">
						<button type="button" class="cfd-trigger" disabled>Select Job</button>
					</div>
					<div class="tr-action">
						<button type="button" class="sd-btn sd-btn-primary" disabled>
							<Download :size="14" stroke-width="2" /> Download Tracking Report
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue";
import { Download } from "@lucide/vue";
import { exportUrl } from "./api";
import CustomerFilterDropdown from "../../components/CustomerFilterDropdown.vue";

const selectedCustomers = ref([]);

const trackingReportHref = computed(() =>
	exportUrl("trackingReport", { customers: selectedCustomers.value })
);
</script>

<style scoped>
.tr-table {
	display: flex;
	flex-direction: column;
}

.tr-row {
	display: grid;
	grid-template-columns: 220px 200px 1fr;
	align-items: center;
	gap: 16px;
	padding: 12px 0;
	border-top: 1px solid var(--sd-border-soft);
}

.tr-row:first-child {
	border-top: none;
}

.tr-name {
	font-size: 14px;
	font-weight: 600;
	color: var(--sd-text);
	display: flex;
	align-items: center;
	gap: 8px;
}

.tr-soon {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.03em;
	color: var(--sd-text-faint);
	background: var(--sd-surface-alt);
	border: 1px solid var(--sd-border);
	padding: 2px 6px;
	border-radius: 999px;
}

.tr-filter .cfd-trigger {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 8px 12px;
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius-sm);
	background: var(--sd-surface);
	color: var(--sd-text-faint);
	font-size: 13px;
	font-family: inherit;
}

.tr-filter button[disabled],
.tr-action button[disabled] {
	opacity: 0.5;
	cursor: not-allowed;
}
</style>
