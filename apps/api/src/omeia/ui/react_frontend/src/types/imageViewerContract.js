/**
 * @typedef {Object} ImageDimensions
 * @property {number[]} shape
 * @property {string} axes
 */

/**
 * @typedef {Object} ImageMetadata
 * @property {string} asset_id
 * @property {'tiff'|'ome_tiff'|'unsupported'} format
 * @property {string} streaming_status
 * @property {number} size_bytes
 * @property {string|null} inspected_at
 * @property {ImageDimensions|null} dimensions
 * @property {number|null} channels
 * @property {string|null} dtype
 * @property {number} pyramid_levels
 * @property {number} series_count
 * @property {boolean} ome_xml_present
 * @property {boolean} tile_ready
 * @property {boolean} thumbnail_ready
 * @property {string[]} errors
 */

/**
 * @typedef {Object} ImageViewerManifest
 * @property {string} asset_id
 * @property {string} format
 * @property {string} streaming_status
 * @property {ImageDimensions|null} dimensions
 * @property {number|null} width
 * @property {number|null} height
 * @property {number|null} channels
 * @property {number} pyramid_levels
 * @property {number} tile_size
 * @property {boolean} tile_ready
 * @property {string} thumbnail_url
 * @property {string} metadata_url
 * @property {string} stream_url
 * @property {string} viewer_route
 * @property {boolean} ome_xml_present
 */

/**
 * @typedef {Object} ImageViewerAsset
 * @property {string} asset_id
 * @property {string} [filename]
 * @property {string} [display_title]
 * @property {boolean} is_streamable_image
 * @property {ImageMetadata|null} image_metadata
 * @property {string|null} thumbnail_url
 * @property {string|null} viewer_url
 */

export {};
