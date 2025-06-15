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

const rows = document.querySelectorAll('.data-table tbody tr');

const searchInput = document.querySelector('.search-container input');
const searchContainer = document.querySelector('.search-container');

const editBtn = document.getElementById("editObjectBtn");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const editObjectModal = document.getElementById("editObjectadd");
const editForm = document.getElementById("editObjectForm");
const editObjectPop = document.getElementById('editObjectPop');
const editObjectForm = document.getElementById('editObjectForm');
const editObjectNameInput = document.getElementById('editObjectName');
const editFileInput = document.getElementById('editFileInput');
const editFileList = document.getElementById('editFileList');
const editObjectBtn = document.getElementById('editObjectBtn');
const editDropArea = document.getElementById("editDropArea");
const editCancelBtn = document.getElementById("editCancelBtn");

if (editBtn) {
    editBtn.style.display = 'flex';
    editBtn.disabled = true;
}

let droppedFiles = [];
let currentEditObjectId = null;
let editDroppedFiles = [];


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

async function refreshObjectsTable(sortBy = 'updated') {
    try {
        const response = await fetch(`/objects?sort=${sortBy}`);
        const result = await response.json();
        
        if (result.success && result.objects) {
            updateObjectsTable(result.objects);
            await refreshFolderInfo();
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

    // Disable and reset editBtn
    if (typeof editBtn !== 'undefined' && editBtn) {
        editBtn.disabled = true;
        editBtn.style.backgroundColor = '';
        editBtn.style.borderColor = '';
    }
}

function attachRowEventListeners(row) {
    row.addEventListener('click', async () => {
        const allRows = document.querySelectorAll('.data-table tbody tr');
        allRows.forEach(r => r.classList.remove('selected'));
        row.classList.add('selected');

        const cells = row.querySelectorAll('td');
        const objectName = cells[1].innerText;
        const createdBy = cells[4].innerText;
        
        // GET THE OBJECT ID FROM THE ROW
        const objectId = row.dataset.objectId || row.getAttribute('data-object-id');
        
        // SET THE GLOBAL WINDOW VARIABLE - THIS WAS MISSING!
        window.currentObjectId = objectId;
        
        console.log('Row clicked - Object ID set to:', objectId); // Debug log

        document.getElementById('addObjectName').innerText = objectName;

        const detailTable = document.querySelector('#filesPop .file-table table tbody');
        if (detailTable) {
            detailTable.innerHTML = '';
        }

        try {
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

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US') + ' ' + date.toLocaleTimeString('en-US');
    } catch (error) {
        return dateString;
    }
}
// End of Dashboard Object Lists



// Add Object
if (batchNameInput) {
    batchNameInput.addEventListener('invalid', () => {
        batchNameInput.classList.add('error');
    });
    
    batchNameInput.addEventListener('input', () => {
        batchNameInput.classList.remove('error');
    });
}

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
                if (add) add.style.display = "none";
                if (batchNameInput) batchNameInput.value = '';
                droppedFiles = [];
                renderFileList();
                hideMessages();
                
                await refreshObjectsTable();
                
                setTimeout(() => {
                    showSuccessPopup(`Successfully uploaded ${result.files.length} files to "${result.object_name}"`);
                    setTimeout(() => {
                        closeSuccessPopup();
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


// Drag & Drop
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

		if (items.length > 0 && (!batchNameInput.value || batchNameInput.value.trim() === '')) {
			const entry = items[0].webkitGetAsEntry();
			if (entry && entry.isDirectory) {
				const folderName = entry.name;
				if (batchNameInput) batchNameInput.value = folderName;
			}
		}

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

if (fileInput) {
	fileInput.addEventListener("change", () => {
		const files = Array.from(fileInput.files);

		for (const file of files) {
			if (file.type.startsWith("image/")) {
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
		fileInput.value = '';
	});
}

async function traverseFileTree(entry) {
    if (entry.isFile) {
        return new Promise(resolve => {
            entry.file(file => {
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

function formatFileSize(bytes) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));

	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function validateForm() {
    let isValid = true;

    const batchNameInput = document.getElementById('batchName');
    const dropArea = document.getElementById('dropArea');
    
    if (batchNameInput) batchNameInput.classList.remove('error');
    if (dropArea) dropArea.classList.remove('error');

    const objectName = batchNameInput ? batchNameInput.value.trim() : '';
    if (!objectName) {
        if (batchNameInput) batchNameInput.classList.add('error');
        isValid = false;
    }
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
        formData.append('merge', 'true');
        
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
            await refreshObjectsTable();
            
            setTimeout(() => {
                showSuccessPopup(`Successfully merged ${result.files.length} files to "${result.object_name}"`);
                setTimeout(() => {
                    closeSuccessPopup();
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
                openObjectDetailsFromSearch(obj);
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

async function openObjectDetailsFromSearch(obj) {
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
    window.currentObjectId = obj.objectId;
    console.log('Search opened object - Object ID set to:', obj.objectId);
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
function applySort(sortBy) {
    console.log("Sorting by:", sortBy);
    sessionStorage.setItem('objectsSort', sortBy);
    refreshObjectsTable(sortBy);
}

function getSavedSort() {
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
    const savedSort = getSavedSort();
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


const closeModalBtn = document.getElementById('');
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



// Edit Object Form
function openObjectDetails(objectId, objectName) {
    window.currentObjectId = objectId;
    document.getElementById('addObjectName').textContent = objectName;
    document.getElementById('filesPop').style.display = 'flex';
}

// Edit button click handler
document.addEventListener('click', function (event) {
    const editBtn = event.target.closest('.edit-btn');
    if (!editBtn) return;
    
    const currentObjectName = document.getElementById('addObjectName')?.textContent?.trim() || '';
    const currentEditObjectId = window.currentObjectId || null;
    
    console.log('Current Object ID:', currentEditObjectId);
    console.log('Current Object Name:', currentObjectName);
    
    if (!currentEditObjectId || !currentObjectName) {
        alert('Error: Missing object name or ID.');
        console.error('Missing data:', { objectId: currentEditObjectId, objectName: currentObjectName });
        return;
    }
    
    // Set the object name in the edit form
    if (editObjectNameInput) {
        editObjectNameInput.value = currentObjectName;
    }
    
    // Close the details popup and open edit popup
    document.getElementById('filesPop').style.display = 'none';
    const popup = document.getElementById('editObjectPop');
    popup.style.display = 'flex';
    popup.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    popup.style.zIndex = '9999';
});

// Input validation handlers
if (editObjectNameInput) {
    editObjectNameInput.addEventListener('invalid', () => {
        editObjectNameInput.classList.add('error');
    });
    
    editObjectNameInput.addEventListener('input', () => {
        editObjectNameInput.classList.remove('error');
    });
}

// Edit Form Submit Handler
if (editForm) {
    editForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const objectId = window.currentObjectId;
        const objectName = editObjectNameInput.value.trim();
        
        if (!objectId) {
            alert('Error: No object selected for editing.');
            return;
        }
        
        if (!objectName) {
            editObjectNameInput.classList.add('error');
            alert('Error: Object name is required.');
            return;
        }

        // Remove error styling
        editObjectNameInput.classList.remove('error');
        if (editDropArea) editDropArea.classList.remove('error');
        
        hideEditMessages();
        setEditUploadState(true);
        
        try {
            const formData = new FormData();
            formData.append('objectId', objectId);
            formData.append('editObjectName', objectName);
            
            // Add files from drag/drop
            editDroppedFiles.forEach((file, index) => {
                formData.append('files', file);
            });
            
            // Add files from file input
            if (editFileInput && editFileInput.files.length > 0) {
                for (let i = 0; i < editFileInput.files.length; i++) {
                    formData.append('files', editFileInput.files[i]);
                }
            }
            
            const response = await fetch('/edit_object', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                // Clean up form
                closeEditPopup();
                editDroppedFiles = [];
                renderEditFileList();
                hideEditMessages();
                
                // Refresh the table if function exists
                if (typeof refreshObjectsTable === 'function') {
                    await refreshObjectsTable();
                }
                
                alert('Successfully updated "' + result.object_name + '"');
                
            } else {
                if (response.status === 409 || result.conflict === true || 
                    (result.error && result.error.toLowerCase().includes('already exists'))) {
                    
                    // Simple conflict handling
                    if (confirm('Object name already exists. Would you like to merge the files?')) {
                        // Add merge parameter and retry
                        formData.append('merge', 'true');
                        const mergeResponse = await fetch('/edit_object', {
                            method: 'POST',
                            body: formData
                        });
                        const mergeResult = await mergeResponse.json();
                        
                        if (mergeResult.success) {
                            closeEditPopup();
                            alert('Successfully merged files to "' + mergeResult.object_name + '"');
                        } else {
                            alert('Merge failed: ' + (mergeResult.error || 'Unknown error'));
                        }
                    }
                } else if (response.status === 401) {
                    alert('Session expired. Please log in again.');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    alert('Error: ' + (result.error || 'Update failed. Please try again.'));
                }
            }
            
        } catch (error) {
            console.error('Edit error:', error);
            if (error.name === 'TypeError' || error.message.includes('Failed to fetch')) {
                alert('Network error. Please check your connection and try again.');
            } else {
                alert('An unexpected error occurred. Please try again.');
            }
        } finally {
            setEditUploadState(false);
        }
    });
}

// Edit Cancel Button Handler
if (editCancelBtn) {
    editCancelBtn.addEventListener("click", () => {
        closeEditPopup();
    });
}

// Edit Drag & Drop Functionality
if (editDropArea) {
    editDropArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        editDropArea.style.borderColor = "#fd1717";
    });

    editDropArea.addEventListener("dragleave", () => {
        editDropArea.style.borderColor = "#ccc";
    });

    editDropArea.addEventListener("drop", async (e) => {
        e.preventDefault();
        editDropArea.style.borderColor = "#ccc";

        const items = e.dataTransfer.items;

        for (const item of items) {
            const entry = item.webkitGetAsEntry();
            if (entry) await traverseEditFileTree(entry);
        }

        renderEditFileList();
    });

    // Browse button functionality
    const editBrowseBtn = editDropArea.querySelector('.browse-btn');
    if (editBrowseBtn) {
        editBrowseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (editFileInput) editFileInput.click();
        });
    }

    const editDropHeader = editDropArea.querySelector('.drop-header');
    if (editDropHeader && !editBrowseBtn) {
        editDropHeader.addEventListener("click", (e) => {
            if (
                e.target === editDropHeader ||
                e.target.classList.contains('browse-btn') ||
                e.target.classList.contains('or-text')
            ) {
                if (editFileInput) editFileInput.click();
            }
        });
    }
}

// Edit File Input Handler
if (editFileInput) {
    editFileInput.addEventListener("change", () => {
        const files = Array.from(editFileInput.files);

        for (const file of files) {
            if (file.type.startsWith("image/")) {
                const exists = editDroppedFiles.some(existingFile =>
                    existingFile.name === file.name && existingFile.size === file.size
                );
                if (!exists) {
                    editDroppedFiles.push(file);
                }
            }
        }

        renderEditFileList();
        editFileInput.value = '';
    });
}

// Helper Functions
async function traverseEditFileTree(entry) {
    if (entry.isFile) {
        return new Promise(resolve => {
            entry.file(file => {
                if (file.type.startsWith("image/")) {
                    const exists = editDroppedFiles.some(existingFile =>
                        existingFile.name === file.name && existingFile.size === file.size
                    );
                    if (!exists) {
                        editDroppedFiles.push(file);
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
                    await traverseEditFileTree(subEntry);
                }
                resolve();
            });
        });
    }
}

function renderEditFileList() {
    if (!editFileList) return;

    if (editDropArea && editDroppedFiles.length > 0) {
        editDropArea.classList.remove('error');
    }

    editFileList.innerHTML = '';

    editDroppedFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="file-info">
                <div class="file-name-row">
                    <span class="file-name">${file.name}</span>
                    <button type="button" class="remove-btn" onclick="removeEditFile(${index})">&times;</button>
                </div>
                <span class="file-size">${formatFileSize(file.size)}</span>
            </div>
        `;
        editFileList.appendChild(li);
    });
}

function removeEditFile(index) {
    event.stopPropagation();
    editDroppedFiles.splice(index, 1);
    renderEditFileList();
}

function setEditUploadState(isUploading) {
    const editUploadBtn = document.querySelector('#editObjectForm .upload-btn');
    const editCancelBtn = document.getElementById('editCancelBtn');

    if (editUploadBtn) {
        editUploadBtn.disabled = isUploading;
        editUploadBtn.textContent = isUploading ? 'Saving...' : 'Save Changes';
    }
    if (editCancelBtn) {
        editCancelBtn.disabled = isUploading;
    }
}

function hideEditMessages() {
    const editErrorMessage = document.getElementById("editErrorMessage");
    const editSuccessMessage = document.getElementById("editSuccessMessage");
    
    if (editErrorMessage) editErrorMessage.style.display = 'none';
    if (editSuccessMessage) editSuccessMessage.style.display = 'none';
}

function closeEditPopup() {
    const editObjectPop = document.getElementById('editObjectPop');
    
    if (editObjectPop) {
        editObjectPop.style.display = 'none';
    }
    if (editObjectNameInput) {
        editObjectNameInput.value = '';
        editObjectNameInput.classList.remove('error');
    }
    if (editFileInput) {
        editFileInput.value = '';
    }
    if (editDropArea) {
        editDropArea.classList.remove('error');
    }
    
    editDroppedFiles = [];
    renderEditFileList();
    hideEditMessages();
    
    console.log('Edit popup closed and reset');
}

// File size formatter (add this if not already present)
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}