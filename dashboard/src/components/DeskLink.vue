<template>
	<a
		class="sd-desklink"
		:class="{ 'sd-desklink-plain': plain }"
		:href="href"
		target="_blank"
		rel="noopener"
		:title="`Open ${doctype} ${name} in Frappe Desk`"
		@click.stop
	>
		<span v-if="!iconOnly" class="sd-desklink-label">{{ label || name }}</span>
		<ExternalLink v-if="!hideIcon" :size="iconSize" stroke-width="2" class="sd-desklink-icon" />
	</a>
</template>

<script setup>
import { computed } from "vue";
import { ExternalLink } from "@lucide/vue";
import { deskUrl } from "../deskLink";

// Renders a document reference as a link that opens the record in Frappe Desk
// for editing (new tab). Use in any table cell / drawer header where a job or
// invoice id appears. `@click.stop` so clicking the link never also triggers a
// row's open-drawer handler.
const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	label: { type: String, default: "" },
	// `plain` reads as normal text until hovered (for dense tables); default
	// styling shows it as an accented link.
	plain: { type: Boolean, default: false },
	hideIcon: { type: Boolean, default: false },
	// Render just the external-link icon (dense table cells beside another link).
	iconOnly: { type: Boolean, default: false },
	iconSize: { type: Number, default: 13 },
});

const href = computed(() => deskUrl(props.doctype, props.name));
</script>
