# Forwarding Job Folder Management Utility

**Location**: `freightmas/utils/forwarding_job_folder.py`

This utility provides automatic folder creation and file management for Forwarding Jobs in FreightMas.

## Features

- **Automatic Folder Creation**: Creates structured folders for each forwarding job
- **File Organization**: Moves file attachments to job-specific folders  
- **Folder Renaming**: Updates folder names when job details change
- **Safe Operations**: Uses `frappe.db.set_value` for atomic file updates
- **Error Handling**: Graceful fallback when folder operations fail

## Folder Structure

```
Home/
└── Forwarding Jobs/
    └── <YEAR>/
        └── <JOBNAME - CUSTOMERREFERENCE>/
            ├── attachment1.pdf
            ├── attachment2.xlsx
            └── ...
```

## Usage

```python
from freightmas.utils.forwarding_job_folder import ForwardingJobFolderManager

# Get job document
job_doc = frappe.get_doc("Forwarding Job", "FWJB-00001-25")

# Create folder
folder_path = ForwardingJobFolderManager.create_job_folder(job_doc)

# Move files to folder
moved_files = ForwardingJobFolderManager.move_files_to_job_folder(job_doc)
```

## Integration

The utility is automatically integrated via document hooks in `hooks.py`:

```python
"Forwarding Job": {
    "after_insert": "freightmas.utils.forwarding_job_folder.handle_forwarding_job_folder_creation",
    "on_update": "freightmas.utils.forwarding_job_folder.handle_forwarding_job_folder_creation", 
    "before_rename": "freightmas.utils.forwarding_job_folder.handle_forwarding_job_folder_rename"
},
"File": {
    "after_insert": "freightmas.utils.forwarding_job_folder.handle_file_move_to_job_folder",
    "on_update": "freightmas.utils.forwarding_job_folder.handle_file_move_to_job_folder"
}
```