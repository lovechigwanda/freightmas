<template>
	<div class="sd-card sd-documents-card" :class="{ 'sd-documents-card--compact': compactEmpty && !hasDocuments && !loading && !error }">
		<div class="sd-card-title"><span class="sd-card-title-main">Documents</span></div>

		<div v-if="loading">
			<div class="cc-row-skeleton cc-skeleton" v-for="i in 4" :key="i"></div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red); padding: 20px 0;">{{ error }}</div>
		<div v-else>
			<template v-if="hasDocuments">
				<div class="sd-documents-panel-title">
					Outgoing
					<span class="sd-documents-count">{{ documents.outgoing.length }}</span>
				</div>
				<p class="sd-muted sd-documents-intro">Documents shared with you by your account team.</p>
				<ul class="sd-documents-list">
					<li v-for="row in documents.outgoing" :key="row.name" class="sd-documents-list-item">
						<div>
							<div class="sd-documents-list-label">{{ row.document_label }}</div>
							<div class="sd-muted sd-documents-list-file">{{ row.file_name || "–" }}</div>
						</div>
						<a
							class="sd-documents-download"
							:href="downloadUrl(row.name)"
							target="_blank"
							rel="noopener"
						>
							Download
						</a>
					</li>
				</ul>
			</template>
			<p v-else-if="compactEmpty" class="sd-documents-empty-compact sd-muted">
				No documents shared yet.
			</p>
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
import { computed } from "vue";
import { FileText } from "@lucide/vue";
import EmptyState from "./EmptyState.vue";

const props = defineProps({
	documents: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	downloadUrl: { type: Function, required: true },
	compactEmpty: { type: Boolean, default: false },
});

const hasDocuments = computed(() => (props.documents?.outgoing?.length || 0) > 0);
</script>
