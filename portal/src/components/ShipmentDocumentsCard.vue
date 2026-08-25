<template>
	<div class="sd-card">
		<div class="sd-card-title"><span class="sd-card-title-main">Documents</span></div>

		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red); padding: 20px 0;">{{ error }}</div>
		<div v-else>
			<div class="sd-documents-panel-title">
				Outgoing
				<span class="sd-documents-count">{{ documents?.outgoing?.length || 0 }}</span>
			</div>
			<p class="sd-muted sd-documents-intro">Documents shared with you by your account team.</p>
			<table class="sd-table sd-documents-table" v-if="documents?.outgoing?.length">
				<thead>
					<tr>
						<th>Document</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in documents.outgoing" :key="row.name">
						<td>
							<div>{{ row.document_label }}</div>
							<div class="sd-muted" style="font-size: 12px;">{{ row.file_name || "–" }}</div>
						</td>
						<td class="sd-right">
							<a
								class="sd-table-link"
								:href="downloadUrl(row.name)"
								target="_blank"
								rel="noopener"
							>
								Download
							</a>
						</td>
					</tr>
				</tbody>
			</table>
			<EmptyState
				v-else
				:icon="FileText"
				title="No outgoing documents yet"
				sub="Your team has not shared any documents for this shipment."
			/>
		</div>
	</div>
</template>

<script setup>
import { FileText } from "@lucide/vue";
import EmptyState from "./EmptyState.vue";

defineProps({
	documents: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	downloadUrl: { type: Function, required: true },
});
</script>
