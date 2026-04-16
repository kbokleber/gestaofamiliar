const FILE_EXTENSION_TO_MIME: Record<string, string> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  pdf: 'application/pdf',
  heic: 'image/heic',
  heif: 'image/heif',
}

const ALLOWED_MIME_TYPES = new Set(Object.values(FILE_EXTENSION_TO_MIME))

export const IMAGE_AND_DOCUMENT_ACCEPT =
  'image/jpeg,image/jpg,.jpg,.jpeg,image/png,.png,image/gif,.gif,application/pdf,.pdf,image/heic,image/heif,.heic,.heif'

export function getFileExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() || ''
}

export function getNormalizedMimeType(file: File): string {
  const extension = getFileExtension(file.name)
  const mimeFromExtension = FILE_EXTENSION_TO_MIME[extension]

  if (file.type && ALLOWED_MIME_TYPES.has(file.type)) {
    return file.type === 'image/jpg' ? 'image/jpeg' : file.type
  }

  if (mimeFromExtension) {
    return mimeFromExtension
  }

  return file.type || ''
}

export function isAllowedUploadFile(file: File): boolean {
  return ALLOWED_MIME_TYPES.has(getNormalizedMimeType(file))
}
