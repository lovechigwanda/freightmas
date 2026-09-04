<template>
	<div class="sd-card sd-documents-card sd-documents-card--full">
		<div class="sd-card-title"><span class="sd-card-title-main">Documents</span></div>

		<div v-if="loading" class="sd-documents-split">
			<div class="sd-documents-panel">
				<div class="cc-row-skeleton cc-skeleton" v-for="i in 3" :key="'out-' + i"></div>
			</div>
			<div class="sd-documents-panel">
				<div class="cc-row-skeleton cc-skeleton" v-for="i in 3" :key="'in-' + i"></div>
			</div>
		</div>
		<div v-else-if="error" class="sd-state" style="color: var(--sd-red); padding: 20px 0;">{{ error }}</div>
		<div v-else class="sd-documents-split">
			<section class="sd-documents-panel">
				<div class="sd-documents-panel-title">
					Outgoing
					<span v-if="hasOutgoing" class="sd-documents-count">{{ documents.outgoing.length }}</span>
				</div>
				<p class="sd-muted sd-documents-intro">Documents shared with you by your account team.</p>
				<ul v-if="hasOutgoing" class="sd-documents-list">
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
				<p v-else class="sd-documents-empty-compact sd-muted">No documents shared yet.</p>
			</section>

			<section class="sd-documents-panel">
				<div class="sd-documents-panel-title">
					Incoming
					<span v-if="hasIncoming" class="sd-documents-count">{{ incomingRows.length }}</span>
				</div>
				<p class="sd-muted sd-documents-intro">
					Upload documents requested by your account team or submit additional files.
				</p>

				<ul v-if="hasIncoming" class="sd-documents-list">
					<li v-for="row in incomingRows" :key="row.name" class="sd-documents-list-item">
						<div>
							<div class="sd-documents-list-label">{{ row.document_label }}</div>
							<div class="sd-muted sd-documents-list-file">
								<template v-if="row.file_name">{{ row.file_name }}</template>
								<template v-else>Awaiting upload</template>
								<span v-if="row.is_verified" class="sd-documents-verified"> · Verified</span>
							</div>
						</div>
						<div class="sd-documents-actions">
							<a
								v-if="row.can_download"
								class="sd-documents-download"
								:href="downloadUrl(row.name)"
								target="_blank"
								rel="noopener"
							>
								Download
							</a>
							<button
								v-if="row.can_upload"
								type="button"
								class="sd-btn sd-btn-primary sd-documents-upload-btn"
								:disabled="isUploading(row.name)"
								@click="triggerRowUpload(row)"
							>
								{{ row.file_name ? "Replace" : "Upload" }}
							</button>
						</div>
					</li>
				</ul>

				<div v-if="jobName" class="sd-documents-adhoc">
					<div class="sd-documents-adhoc-title">Submit additional document</div>
					<div class="sd-documents-adhoc-form">
						<select v-model="adHocDocument" class="sd-documents-select" :disabled="adHocUploading">
							<option value="">Select document type</option>
							<option v-for="docType in documentTypes" :key="docType" :value="docType">
								{{ docType }}
							</option>
						</select>
						<label class="sd-btn sd-documents-file-btn" :class="{ 'sd-documents-file-btn--disabled': adHocUploading }">
							{{ adHocFile ? adHocFile.name : "Choose file" }}
							<input
								type="file"
								class="sd-documents-file-input"
								:disabled="adHocUploading"
								accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
								@change="onAdHocFileChange"
							/>
						</label>
						<button
							type="button"
							class="sd-btn sd-btn-primary"
							:disabled="!canSubmitAdHoc"
							@click="submitAdHocUpload"
						>
							{{ adHocUploading ? "Uploading…" : "Submit" }}
						</button>
					</div>
					<p v-if="uploadError" class="sd-documents-upload-error">{{ uploadError }}</p>
					<p v-if="uploadSuccess" class="sd-documents-upload-success">{{ uploadSuccess }}</p>
				</div>

				<input
					ref="rowFileInput"
					type="file"
					class="sd-documents-file-input"
					accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
					@change="onRowFileSelected"
				/>
			</section>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api as documentsApi } from "../api/documents";

const props = defineProps({
	documents: { type: Object, default: null },
	loading: { type: Boolean, default: false },
	error: { type: String, default: "" },
	downloadUrl: { type: Function, required: true },
	jobName: { type: String, default: "" },
});

const emit = defineEmits(["refresh"]);

const documentTypes = ref([]);
const adHocDocument = ref("");
const adHocFile = ref(null);
const adHocUploading = ref(false);
const uploadError = ref("");
const uploadSuccess = ref("");
const rowFileInput = ref(null);
const activeRow = ref(null);
const uploadingRows = ref({});

const incomingRows = computed(() => props.documents?.incoming || []);
const hasOutgoing = computed(() => (props.documents?.outgoing?.length || 0) > 0);
const hasIncoming = computed(() => incomingRows.value.length > 0);
const canSubmitAdHoc = computed(
	() => !!props.jobName && !!adHocDocument.value && !!adHocFile.value && !adHocUploading.value,
);

function isUploading(rowName) {
	return !!uploadingRows.value[rowName] || adHocUploading.value;
}

async function loadDocumentTypes() {
	if (!props.jobName) return;
	try {
		documentTypes.value = await documentsApi.getUploadDocumentTypes();
	} catch (e) {
		documentTypes.value = [];
	}
}

function triggerRowUpload(row) {
	uploadError.value = "";
	uploadSuccess.value = "";
	activeRow.value = row;
	rowFileInput.value?.click();
}

async function onRowFileSelected(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	const row = activeRow.value;
	activeRow.value = null;
	if (!file || !row || !props.jobName) return;

	uploadError.value = "";
	uploadSuccess.value = "";
	uploadingRows.value = { ...uploadingRows.value, [row.name]: true };
	try {
		await documentsApi.uploadDocument(props.jobName, { file, checklistRow: row.name });
		uploadSuccess.value = `${row.document_label} uploaded successfully.`;
		emit("refresh");
	} catch (e) {
		uploadError.value = e.message || "Upload failed.";
	} finally {
		const next = { ...uploadingRows.value };
		delete next[row.name];
		uploadingRows.value = next;
	}
}

function onAdHocFileChange(event) {
	adHocFile.value = event.target.files?.[0] || null;
	uploadError.value = "";
	uploadSuccess.value = "";
}

async function submitAdHocUpload() {
	if (!canSubmitAdHoc.value) return;
	adHocUploading.value = true;
	uploadError.value = "";
	uploadSuccess.value = "";
	try {
		await documentsApi.uploadDocument(props.jobName, {
			file: adHocFile.value,
			document: adHocDocument.value,
		});
		uploadSuccess.value = `${adHocDocument.value} uploaded successfully.`;
		adHocDocument.value = "";
		adHocFile.value = null;
		emit("refresh");
	} catch (e) {
		uploadError.value = e.message || "Upload failed.";
	} finally {
		adHocUploading.value = false;
	}
}

watch(
	() => props.jobName,
	(jobName) => {
		if (jobName) loadDocumentTypes();
	},
	{ immediate: true },
);

onMounted(() => {
	if (props.jobName) loadDocumentTypes();
});
</script>
