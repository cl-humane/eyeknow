/// DOM elements
const add = document.getElementById("add");
const dropArea = document.getElementById("dropArea");
const batchNameInput = document.getElementById("batchName");
const cancelBtn = document.getElementById("cancelBtn");
const fileList = document.getElementById("fileList");
const fileInput = document.getElementById("fileInput");
const uploadForm = document.getElementById("uploadForm");
const errorMessage = document.getElementById("errorMessage");
const successMessage = document.getElementById("successMessage");

const editBtn = document.getElementById("editObjectBtn");
const rows = document.querySelectorAll('.data-table tbody tr');
const editObjectModal = document.getElementById("editObjectModal");
const editForm = document.getElementById("editObjectForm");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const searchInput = document.querySelector('.search-container input');
const searchContainer = document.querySelector('.search-container');

if (editBtn) {
    editBtn.style.display = 'flex';
    editBtn.disabled = true;
}

let droppedFiles = [];

function showError(message) {
	if (errorMessage) {
		errorMessage.textContent = message;
		errorMessage.style.display = 'block';
	}
	if (successMessage) {
		successMessage.style.display = 'none';
	}
}

function showSuccess(message) {
	if (successMessage) {
		successMessage.textContent = message;
		successMessage.style.display = 'block';
	}
	if (errorMessage) {
		errorMessage.style.display = 'none';
	}
}

function hideMessages() {
	if (errorMessage) errorMessage.style.display = 'none';
	if (successMessage) successMessage.style.display = 'none';
}

function setUploadState(isUploading) {
	const uploadBtn = document.querySelector('.upload-btn');
	const cancelBtn = document.getElementById('cancelBtn');

	if (uploadBtn) {
		uploadBtn.disabled = isUploading;
		uploadBtn.textContent = isUploading ? 'Uploading...' : 'Upload';
	}
	if (cancelBtn) {
		cancelBtn.disabled = isUploading;
	}
}



// Dashboard Object Lists
async function refreshFolderInfo() {
    try {
        const response = await fetch('/folder-info');
        const data = await response.json();

        if (data.success && data.folder) {
            const lastUpdatedElement = document.getElementById('lastUpdated');
            const dateCreatedElement = document.getElementById('dateCreated');

            if (lastUpdatedElement) {
                lastUpdatedElement.textContent = data.folder.last_updated;
            }
            if (dateCreatedElement) {
                dateCreatedElement.textContent = data.folder.date_created;
            }
        } else {
            console.error('Failed to refresh folder info:', data.error);
        }
    } catch (err) {
        console.error('Error fetching folder info:', err);
    }
}

function updateFolderDisplay(folderData) {
    const folderNameElement = document.querySelector('.folder-name');
    if (folderNameElement) {
        folderNameElement.textContent = folderData.folder_name;
    }

    const lastUpdatedElement = document.querySelector('.last-updated');
    if (lastUpdatedElement) {
        lastUpdatedElement.textContent = folderData.last_updated;
    }

    const dateCreatedElement = document.querySelector('.date-created');
    if (dateCreatedElement) {
        dateCreatedElement.textContent = folderData.date_created;
    }
}

// Replace your existing refreshObjectsTable function with this updated version
async function refreshObjectsTable(sortBy = 'updated') {
    try {
        const response = await fetch(`/objects?sort=${sortBy}`);
        const result = await response.json();
        
        if (result.success && result.objects) {
            updateObjectsTable(result.objects);
            await refreshFolderInfo();
        } else {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error refreshing table:', error);
        window.location.reload();
    }
}

function updateObjectsTable(objects) {
    const tableBody = document.querySelector('.data-table tbody');
    if (!tableBody) {
        window.location.reload();
        return;
    }
    tableBody.innerHTML = '';
    objects.forEach((obj, index) => {
        const row = document.createElement('tr');
        row.dataset.objectId = obj.object_id;  
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${obj.object_name}</td>
            <td>${obj.date_created_formatted}</td>
            <td>${obj.date_updated_formatted}</td>
            <td>${obj.created_by_name}</td>
            <td>${obj.size_formatted}</td>
        `;
        attachRowEventListeners(row);
        tableBody.appendChild(row);
    });
    if (editBtn) {
        editBtn.disabled = true;
        editBtn.style.backgroundColor = '';
        editBtn.style.borderColor = '';
    }
}

function attachRowEventListeners(row) {
    let clickTimer = null;

    row.addEventListener('click', () => {
        clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
            const allRows = document.querySelectorAll('.data-table tbody tr');
            allRows.forEach(r => r.classList.remove('selected'));
            row.classList.add('selected');
            if (editBtn) {
                editBtn.disabled = false;
                editBtn.style.backgroundColor = '#747272';
                editBtn.style.borderColor = '#747272';
            }
        }, 250);
    });

    row.addEventListener('dblclick', async () => {
    clearTimeout(clickTimer);
    const cells = row.querySelectorAll('td');
    const objectName = cells[1].innerText;
    const createdBy = cells[4].innerText;

    document.getElementById('addObjectName').innerText = objectName;

    const detailTable = document.querySelector('#filesPop .file-table table tbody');
    if (detailTable) {
        detailTable.innerHTML = ''; // Clear existing content
    }

    try {
        const objectId = row.dataset.objectId || row.getAttribute('data-object-id');
        const response = await fetch(`/object/${objectId}/files`);
        const result = await response.json();

        if (result.success && result.files && result.files.length > 0) {
            result.files.forEach((file, index) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${file.file_name}</td>
                    <td>${formatDate(file.date_created)}</td>
                    <td>${createdBy}</td>
                    <td style="text-align: right;">${formatFileSize(file.size)}</td>
                `;
                detailTable.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td colspan="5" style="text-align: center;">No files found</td>
            `;
            detailTable.appendChild(tr);
        }
    } catch (error) {
        console.error('Error fetching files:', error);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td colspan="5" style="text-align: center;">Error loading files</td>
        `;
        if (detailTable) detailTable.appendChild(tr);
    }

    document.getElementById('filesPop').style.display = 'flex';
});
}

// Helper function to format dates
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US') + ' ' + date.toLocaleTimeString('en-US');
    } catch (error) {
        return dateString;
    }
}

// Drag & Drop functionality
if (dropArea) {
	dropArea.addEventListener("dragover", (e) => {
		e.preventDefault();
		dropArea.style.borderColor = "#fd1717";
	});

	dropArea.addEventListener("dragleave", () => {
		dropArea.style.borderColor = "#ccc";
	});

	dropArea.addEventListener("drop", async (e) => {
		e.preventDefault();
		dropArea.style.borderColor = "#ccc";

		const items = e.dataTransfer.items;

		// Check if it's a folder drop and set batch name only if empty
		if (items.length > 0 && (!batchNameInput.value || batchNameInput.value.trim() === '')) {
			const entry = items[0].webkitGetAsEntry();
			if (entry && entry.isDirectory) {
				const folderName = entry.name;
				if (batchNameInput) batchNameInput.value = folderName;
			}
		}

		// Process all dropped items (ADD to existing files, don't replace)
		for (const item of items) {
			const entry = item.webkitGetAsEntry();
			if (entry) await traverseFileTree(entry);
		}

		renderFileList();
	});

	const browseBtn = dropArea.querySelector('.browse-btn');
	if (browseBtn) {
		browseBtn.addEventListener("click", (e) => {
			e.stopPropagation();
			if (fileInput) fileInput.click();
		});
	}

	const dropHeader = dropArea.querySelector('.drop-header');
	if (dropHeader && !browseBtn) {
		dropHeader.addEventListener("click", (e) => {
			if (
				e.target === dropHeader ||
				e.target.classList.contains('browse-btn') ||
				e.target.classList.contains('or-text')
			) {
				if (fileInput) fileInput.click();
			}
		});
	}
}

// File input change handler
if (fileInput) {
	fileInput.addEventListener("change", () => {
		const files = Array.from(fileInput.files);

		for (const file of files) {
			if (file.type.startsWith("image/")) {
				// Check if file already exists to avoid duplicates
				const exists = droppedFiles.some(existingFile =>
					existingFile.name === file.name && existingFile.size === file.size
				);
				if (!exists) {
					droppedFiles.push(file);
				}
			}
		}

		if (
			files.length > 0 &&
			files[0].webkitRelativePath &&
			(!batchNameInput.value || batchNameInput.value.trim() === '')
		) {
			const folderName = files[0].webkitRelativePath.split("/")[0];
			if (batchNameInput) batchNameInput.value = folderName;
		}

		renderFileList();

		// Reset file input to allow selecting the same files again if needed
		fileInput.value = '';
	});
}

// Traverse file tree for folder drops
async function traverseFileTree(entry) {
	if (entry.isFile) {
		return new Promise(resolve => {
			entry.file(file => {
				// Only add image files and check for duplicates
				if (file.type.startsWith("image/")) {
					const exists = droppedFiles.some(existingFile =>
						existingFile.name === file.name && existingFile.size === file.size
					);
					if (!exists) {
						droppedFiles.push(file);
					}
				}
				resolve();
			});
		});
	} else if (entry.isDirectory) {
		const reader = entry.createReader();
		return new Promise(resolve => {
			reader.readEntries(async entries => {
				for (const subEntry of entries) {
					await traverseFileTree(subEntry);
				}
				resolve();
			});
		});
	}
}

// Render file list with remove buttons
function renderFileList() {
	if (!fileList) return;

    const dropArea = document.getElementById('dropArea');
    if (dropArea && droppedFiles.length > 0) {
        dropArea.classList.remove('error');
    }

	fileList.innerHTML = '';

	droppedFiles.forEach((file, index) => {
		const li = document.createElement('li');
		li.innerHTML = `
			<div class="file-info">
				<div class="file-name-row">
					<span class="file-name">${file.name}</span>
					<button type="button" class="remove-btn" onclick="removeFile(${index})">&times;</button>
				</div>
				<span class="file-size">${formatFileSize(file.size)}</span>
			</div>
		`;
		fileList.appendChild(li);
	});
}

// Remove file function
function removeFile(index) {
	event.stopPropagation();
	droppedFiles.splice(index, 1);
	renderFileList();
}

// Format file size helper function
function formatFileSize(bytes) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));

	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function validateForm() {
    let isValid = true;
    
    // Reset previous error states
    const batchNameInput = document.getElementById('batchName');
    const dropArea = document.getElementById('dropArea');
    
    if (batchNameInput) batchNameInput.classList.remove('error');
    if (dropArea) dropArea.classList.remove('error');
    
    // Check object name
    const objectName = batchNameInput ? batchNameInput.value.trim() : '';
    if (!objectName) {
        if (batchNameInput) batchNameInput.classList.add('error');
        isValid = false;
    }
    
    // Check files
    if (droppedFiles.length === 0) {
        if (dropArea) dropArea.classList.add('error');
        isValid = false;
    }
    
    return isValid;
}



// Success Pop Up
function showSuccessPopup(message) {
    const modal = document.getElementById('successAdd');
    const messageElement = document.getElementById('successPopupMessage');
    if (!modal || !messageElement) {
        console.error('Success modal elements not found');
        return;
    }
    const formattedMessage = formatSuccessMessage(message);
    messageElement.innerHTML = formattedMessage;   
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeSuccessPopup(event) {
    if (event && event.target.closest('.success-content') && event.target !== event.currentTarget) {
        return;
    }
    const modal = document.getElementById('successAdd');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function formatSuccessMessage(message) {
    const fileCountMatch = message.match(/(\d+)\s+files?/);
    const objectNameMatch = message.match(/"([^"]+)"/);
    let formattedMessage = message;
    if (fileCountMatch) {
        const fileCount = fileCountMatch[1];
        const fileText = parseInt(fileCount) === 1 ? 'file' : 'files';
        formattedMessage = formattedMessage.replace(
            fileCountMatch[0], 
            `<span class="file-count">${fileCount} ${fileText}</span>`
        );
    }
    if (objectNameMatch) {
        const objectName = objectNameMatch[1];
        formattedMessage = formattedMessage.replace(
            objectNameMatch[0], 
            `"<span class="object-name">${objectName}</span>"`
        );
    }
    return formattedMessage;
}

// Error Pop Up
function showGeneralErrorPopup(message = null) {
    const modal = document.getElementById('generalError');
    const messageElement = document.getElementById('generalErrorMessage');
    if (!modal || !messageElement) {
        console.error('General error modal elements not found');
        return;
    }
    if (message) {
        messageElement.textContent = message;
    }
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeGeneralErrorPopup(event) {
    if (event && event.target.closest('.error-content') && event.target !== event.currentTarget) {
        return;
    }
    const modal = document.getElementById('generalError');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function retryUpload() {
    closeGeneralErrorPopup();
    if (uploadForm) {
        uploadForm.dispatchEvent(new Event('submit'));
    }
}

// Conflict Pop Up
function showConflictPopup(objectName) {
    const modal = document.getElementById('conflictPopup');
    const objectNameElement = document.getElementById('conflictObjectName');
    if (!modal || !objectNameElement) {
        console.error('Conflict modal elements not found');
        return;
    }
    objectNameElement.textContent = objectName;
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeConflictPopup(event) {
    if (event && event.target.closest('.conflict-content') && event.target !== event.currentTarget) {
        return;
    }
    const modal = document.getElementById('conflictPopup');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

function closeConflictAndForm() {
    const modal = document.getElementById('conflictPopup');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
    const batchNameInput = document.getElementById('batchName');
    if (batchNameInput) {
        batchNameInput.classList.remove('error');
    }
    const dropArea = document.getElementById('dropArea');
    if (dropArea) {
        dropArea.classList.remove('error');
    }
    if (typeof hideMessages === 'function') {
        hideMessages();
    }
}

// Merge Pop Up
function handleMerge() {
    closeConflictPopup();
    const objectName = document.getElementById('conflictObjectName').textContent;
    performMergeUpload(objectName);
}

async function performMergeUpload(objectName) {
    try {
        setUploadState(true);
        
        const formData = new FormData();
        formData.append('batchName', objectName);
        formData.append('merge', 'true'); // Flag to indicate merge operation
        
        droppedFiles.forEach((file, index) => {
            formData.append('files', file);
        });
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Clean up form
            if (add) add.style.display = "none";
            if (batchNameInput) batchNameInput.value = '';
            droppedFiles = [];
            renderFileList();
            hideMessages();
            
            // FIXED: Refresh data immediately after successful merge
            await refreshObjectsTable(); // This will update both objects and folder info
            
            setTimeout(() => {
                showSuccessPopup(`Successfully merged ${result.files.length} files to "${result.object_name}"`);
                setTimeout(() => {
                    closeSuccessPopup();
                    // Optional: Refresh again after popup closes
                    // refreshObjectsTable();
                }, 3000);
            }, 300);
        } else {
            showError(result.error || 'Merge failed');
        }
    } catch (error) {
        console.error('Merge error:', error);
        showGeneralErrorPopup('Network error during merge. Please check your connection and try again.');
    } finally {
        setUploadState(false);
    }
}


document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeSuccessPopup();
        closeGeneralErrorPopup();
        closeConflictPopup();
    }
});
// End of Pop Up



// Add Object
if (batchNameInput) {
    batchNameInput.addEventListener('invalid', () => {
        batchNameInput.classList.add('error');
    });
    
    batchNameInput.addEventListener('input', () => {
        batchNameInput.classList.remove('error');
    });
}

// Replace your existing upload form event listener with this fixed version:

if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
        if (droppedFiles.length === 0) {
            e.preventDefault();
            const dropArea = document.getElementById('dropArea');
            if (dropArea) dropArea.classList.add('error');
            return;
        }

        const dropArea = document.getElementById('dropArea');
        if (dropArea) dropArea.classList.remove('error');

        e.preventDefault();
        const objectName = batchNameInput.value.trim();
        
        hideMessages();
        setUploadState(true);
        
        try {
            const formData = new FormData();
            formData.append('batchName', objectName);
        
            droppedFiles.forEach((file, index) => {
                formData.append('files', file);
            });
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                // Success case
                if (add) add.style.display = "none";
                if (batchNameInput) batchNameInput.value = '';
                droppedFiles = [];
                renderFileList();
                hideMessages();
                
                // FIXED: Refresh data immediately after successful upload
                await refreshObjectsTable(); // This will update both objects and folder info
                
                setTimeout(() => {
                    showSuccessPopup(`Successfully uploaded ${result.files.length} files to "${result.object_name}"`);
                    setTimeout(() => {
                        closeSuccessPopup();
                        // Optional: Refresh again after popup closes (in case of any timing issues)
                        // refreshObjectsTable();
                    }, 5000);
                }, 300);
                
            } else {
                if (response.status === 409 || result.conflict === true || 
                    (result.error && result.error.toLowerCase().includes('already exists'))) {
                    showConflictPopup(objectName);
                } else if (response.status === 401) {
                    showGeneralErrorPopup('Session expired. Please log in again.');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    showGeneralErrorPopup(result.error || 'Upload failed. Please try again.');
                }
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            if (error.name === 'TypeError' || error.message.includes('Failed to fetch')) {
                showGeneralErrorPopup('Network error. Please check your connection and try again.');
            } else {
                showGeneralErrorPopup('An unexpected error occurred. Please try again.');
            }
        } finally {
            setUploadState(false);
        }
    });
}

if (cancelBtn && add) {
    const addObjectBtn = document.getElementById("addObjectBtn");
    if (addObjectBtn) {
        addObjectBtn.addEventListener("click", () => {
            add.style.display = "flex";
            hideMessages();
        });
    }
    cancelBtn.addEventListener("click", () => {
        add.style.display = "none";
        if (batchNameInput) batchNameInput.value = '';
        droppedFiles = [];
        renderFileList();
        hideMessages();
    });
}
// End of Add Object



// Search Results
const searchDropdown = document.createElement('div');
searchDropdown.className = 'search-dropdown';

if (searchContainer) {
    searchContainer.style.position = 'relative';
    searchContainer.appendChild(searchDropdown);
}

let allObjectsData = [];

function initializeSearchData() {
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    allObjectsData = Array.from(tableRows).map(row => {
        const cells = row.querySelectorAll('td');
        return {
            objectId: row.dataset.objectId,
            objectName: cells[1] ? cells[1].textContent.trim() : '',
            dateCreated: cells[2] ? cells[2].textContent.trim() : '',
            dateUpdated: cells[3] ? cells[3].textContent.trim() : '',
            createdBy: cells[4] ? cells[4].textContent.trim() : '',
            size: cells[5] ? cells[5].textContent.trim() : '',
            element: row
        };
    });
}

function performSearch(query) {
    if (!query || query.trim().length < 1) {
        hideSearchDropdown();
        showAllTableRows();
        return;
    }
    const searchTerm = query.toLowerCase().trim();
    const filteredObjects = allObjectsData.filter(obj => 
        obj.objectName.toLowerCase().includes(searchTerm)
    );
    displaySearchResults(filteredObjects, searchTerm);
    filterTableRows(filteredObjects);
}

function displaySearchResults(results, searchTerm) {
    searchDropdown.innerHTML = '';
    if (results.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'search-result-item no-results';
        noResults.textContent = 'No objects found';
        searchDropdown.appendChild(noResults);
    } else {
        results.forEach(obj => {
            const resultItem = document.createElement('div');
            resultItem.className = 'search-result-item';
            const highlightedName = highlightSearchTerm(obj.objectName, searchTerm);
            resultItem.innerHTML = `
                <div class="search-result-main">
                    ${highlightedName}
                </div>
                <div class="search-result-meta">
                    <span>Created: ${obj.dateCreated}</span> • 
                    <span>Size: ${obj.size}</span> • 
                    <span>By: ${obj.createdBy}</span>
                </div>
            `;
            
            resultItem.addEventListener('click', () => {
                openObjectDetails(obj);
                hideSearchDropdown();
                searchInput.value = obj.objectName;
            });
            searchDropdown.appendChild(resultItem);
        });
    }
    searchDropdown.style.display = 'block';
}

function highlightSearchTerm(text, searchTerm) {
    const regex = new RegExp(`(${escapeRegExp(searchTerm)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function filterTableRows(filteredObjects) {
    const allRows = document.querySelectorAll('.data-table tbody tr');
    const filteredIds = new Set(filteredObjects.map(obj => obj.objectId));
    
    allRows.forEach(row => {
        const objectId = row.dataset.objectId;
        if (filteredIds.has(objectId) || filteredIds.size === 0) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    updateRowNumbers();
}

function showAllTableRows() {
    const allRows = document.querySelectorAll('.data-table tbody tr');
    allRows.forEach(row => {
        row.style.display = '';
    });
    updateRowNumbers();
}

function updateRowNumbers() {
    const visibleRows = document.querySelectorAll('.data-table tbody tr[style=""], .data-table tbody tr:not([style])');
    visibleRows.forEach((row, index) => {
        const firstCell = row.querySelector('td');
        if (firstCell) {
            firstCell.textContent = index + 1;
        }
    });
}

function hideSearchDropdown() {
    searchDropdown.style.display = 'none';
}

async function openObjectDetails(obj) {
    const allRows = document.querySelectorAll('.data-table tbody tr');
    allRows.forEach(r => r.classList.remove('selected'));
    if (obj.element) {
        obj.element.classList.add('selected');
        if (editBtn) {
            editBtn.disabled = false;
            editBtn.style.backgroundColor = '#747272';
            editBtn.style.borderColor = '#747272';
        }
    }
    document.getElementById('addObjectName').innerText = obj.objectName;
    const detailTable = document.querySelector('#filesPop .file-table table tbody');
    if (detailTable) {
        detailTable.innerHTML = '';
    }
    try {
        const response = await fetch(`/object/${obj.objectId}/files`);
        const result = await response.json();

        if (result.success && result.files && result.files.length > 0) {
            result.files.forEach((file, index) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${file.file_name}</td>
                    <td>${formatDate(file.date_created)}</td>
                    <td>${obj.createdBy}</td>
                    <td style="text-align: right;">${formatFileSize(file.size)}</td>
                `;
                detailTable.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td colspan="5" style="text-align: center;">No files found</td>
            `;
            detailTable.appendChild(tr);
        }
    } catch (error) {
        console.error('Error fetching files:', error);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td colspan="5" style="text-align: center;">Error loading files</td>
        `;
        if (detailTable) detailTable.appendChild(tr);
    }
    document.getElementById('filesPop').style.display = 'flex';
}

if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(e.target.value);
        }, 300);
    });
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch(e.target.value);
        }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            navigateDropdown(e.key === 'ArrowDown' ? 1 : -1);
        }
        if (e.key === 'Escape') {
            hideSearchDropdown();
            searchInput.blur();
        }
    });
    searchInput.addEventListener('focus', () => {
        if (searchInput.value.trim()) {
            performSearch(searchInput.value);
        }
    });
}

let selectedDropdownIndex = -1;
function navigateDropdown(direction) {
    const items = searchDropdown.querySelectorAll('.search-result-item:not(.no-results)');
    if (items.length === 0) return;

    if (selectedDropdownIndex >= 0 && items[selectedDropdownIndex]) {
        items[selectedDropdownIndex].classList.remove('selected');
    }

    selectedDropdownIndex += direction;
    if (selectedDropdownIndex < 0) selectedDropdownIndex = items.length - 1;
    if (selectedDropdownIndex >= items.length) selectedDropdownIndex = 0;
    
    if (items[selectedDropdownIndex]) {
        items[selectedDropdownIndex].classList.add('selected');
        items[selectedDropdownIndex].scrollIntoView({ block: 'nearest' });
    }
}

document.addEventListener('click', (e) => {
    if (!searchContainer.contains(e.target)) {
        hideSearchDropdown();
        selectedDropdownIndex = -1;
    }
});

function clearSearch() {
    if (searchInput) {
        searchInput.value = '';
        hideSearchDropdown();
        showAllTableRows();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeSearchData();
});
// End Search Results



// Sort
async function refreshObjectsTable(sortBy = 'updated') {
    try {
        const response = await fetch(`/objects?sort=${sortBy}`);
        const result = await response.json();
        
        if (result.success && result.objects) {
            updateObjectsTable(result.objects);
            await refreshFolderInfo();
            // Update search data after table refresh
            setTimeout(() => {
                initializeSearchData();
            }, 100);
        } else {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error refreshing table:', error);
        window.location.reload();
    }
}

function applySort(sortBy) {
    console.log("Sorting by:", sortBy);
    // Store the current sort preference
    sessionStorage.setItem('objectsSort', sortBy);
    refreshObjectsTable(sortBy);
    updateSortButtonText(sortBy);
}

function getSavedSort() {
    // Get saved sort preference, default to 'updated' if none exists
    return sessionStorage.getItem('objectsSort') || 'updated';
}

document.addEventListener("DOMContentLoaded", () => {
    const sortBtn = document.getElementById("sortBtn");
    const sortDropdown = document.getElementById("sortDropdown");

    if (sortBtn) {
        sortBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            sortDropdown.style.display = sortDropdown.style.display === "block" ? "none" : "block";
        });
    }

    document.addEventListener("click", () => {
        if (sortDropdown) {
            sortDropdown.style.display = "none";
        }
    });

    document.querySelectorAll(".sort-option").forEach(option => {
        option.addEventListener("click", () => {
            const selectedSort = option.getAttribute("data-sort");
            applySort(selectedSort);
            if (sortDropdown) sortDropdown.style.display = "none";
        });
    });

    // Load with saved sort preference and update button text
    const savedSort = getSavedSort();
    updateSortButtonText(savedSort); // Add this line
    applySort(savedSort);
});
// End of Sort



// Logout
document.getElementById('closeaddBtn').addEventListener('click', function() {
    document.getElementById('filesPop').style.display = 'none';
});

function refreshDataTable() {
    refreshObjectsTable();
}

const logoutTrigger = document.getElementById("logoutTrigger");
const logoutModal = document.getElementById("logoutadd");
const cancelLogout = document.getElementById("cancelLogout");

if (logoutTrigger && logoutModal && cancelLogout) {
	logoutTrigger.addEventListener("click", () => {
		logoutModal.style.display = "flex";
	});

	cancelLogout.addEventListener("click", () => {
		logoutModal.style.display = "none";
	});
}
// End of Logout



const closeModalBtn = document.getElementById('closeModalBtn');
if (closeModalBtn) {
	closeModalBtn.addEventListener('click', () => {
		const rowInfoModal = document.getElementById('rowInfoModal');
		if (rowInfoModal) rowInfoModal.style.display = 'none';

		const allRows = document.querySelectorAll('.data-table tbody tr');
		if (allRows) {
			allRows.forEach(r => r.classList.remove('selected'));
		}
		if (editBtn) {
			editBtn.disabled = true;
			editBtn.style.backgroundColor = '';
			editBtn.style.borderColor = '';
		}
	});
}

document.addEventListener('DOMContentLoaded', () => {
    const initialRows = document.querySelectorAll('.data-table tbody tr');
    initialRows.forEach(row => {
        attachRowEventListeners(row);
    });
});

if (editBtn) {
	editBtn.addEventListener("click", () => {
		if (editBtn.disabled) return;

		const selectedRow = document.querySelector('.data-table tbody tr.selected');
		if (!selectedRow) {
			alert("Please select a row first.");
			return;
		}

		const cells = selectedRow.querySelectorAll('td');
		const editObjectName = document.getElementById('editObjectName');
		const editObjectClass = document.getElementById('editObjectClass');
		const editObjectSize = document.getElementById('editObjectSize');

		if (editObjectName && cells[1]) editObjectName.value = cells[1].innerText;
		if (editObjectClass && cells[3]) editObjectClass.value = cells[3].innerText;
		if (editObjectSize && cells[4]) editObjectSize.value = cells[4].innerText;

		if (editObjectModal) editObjectModal.style.display = 'flex';
		if (editObjectName) editObjectName.focus();
	});
}

if (cancelEditBtn && editObjectModal) {
	cancelEditBtn.addEventListener("click", () => {
		editObjectModal.style.display = "none";
	});
}

if (editForm) {
	editForm.addEventListener("submit", (e) => {
		e.preventDefault();
		const selectedRow = document.querySelector('.data-table tbody tr.selected');
		if (!selectedRow) return;

		const cells = selectedRow.querySelectorAll('td');
		const editObjectName = document.getElementById('editObjectName');
		const editObjectClass = document.getElementById('editObjectClass');
		const editObjectSize = document.getElementById('editObjectSize');

		if (editObjectName && cells[1]) cells[1].innerText = editObjectName.value;
		if (editObjectClass && cells[3]) cells[3].innerText = editObjectClass.value;
		if (editObjectSize && cells[4]) cells[4].innerText = editObjectSize.value;

		if (editObjectModal) editObjectModal.style.display = "none";
	});
}

document.addEventListener('click', (event) => {
	const isRowClick = event.target.closest('.data-table tbody tr');
	const isInsideModal = event.target.closest('.add-box') || event.target.closest('.file-container');

	if (!isRowClick && !isInsideModal) {
        const allRows = document.querySelectorAll('.data-table tbody tr');
		allRows.forEach(r => r.classList.remove('selected'));
		if (editBtn) {
			editBtn.disabled = true;
			editBtn.style.backgroundColor = '';
			editBtn.style.borderColor = '';
		}
	}
});