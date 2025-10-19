"""EXIF metadata extraction plugin for Semantic Kernel."""

import importlib.util
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class EXIFReaderPlugin:
    """
    Semantic Kernel plugin for extracting EXIF metadata from images.
    
    Extracts timestamp, camera information, GPS coordinates, and other
    metadata from image files using PIL (Pillow).
    """
    
    def __init__(self):
        """Initialize EXIF reader plugin."""
        self._validate_dependencies()
        logger.info("Initialized EXIFReaderPlugin")
    
    def _validate_dependencies(self):
        """Validate that required libraries are available."""
        pillow_spec = importlib.util.find_spec("PIL")
        if pillow_spec is None:
            logger.warning("PIL (Pillow) not available")
            self.has_pil = False
            raise ImportError(
                "PIL (Pillow) is required for EXIF extraction. "
                "Install it: pip install Pillow"
            )

        # ExifTags lives in a submodule; make sure it exists as well.
        exif_spec = importlib.util.find_spec("PIL.ExifTags")
        if exif_spec is None:
            logger.warning("PIL.ExifTags not available")
            self.has_pil = False
            raise ImportError(
                "PIL.ExifTags is required for EXIF extraction. "
                "Install Pillow with EXIF support."
            )

        self.has_pil = True
    
    @kernel_function(
        name="extract_image_metadata",
        description=(
            "Extract EXIF metadata from image files including timestamp, "
            "camera information, GPS coordinates, and other technical details. "
            "Useful for verifying image authenticity and chronology."
        )
    )
    def extract_metadata(
        self,
        image_bytes: bytes = None,
        image_path: str = None
    ) -> Dict[str, Any]:
        """
        Extract EXIF metadata from an image.
        
        Args:
            image_bytes: Raw image bytes (optional if image_path provided)
            image_path: Path to image file (optional if image_bytes provided)
            
        Returns:
            Dictionary containing:
                - timestamp: Image capture timestamp (ISO format)
                - camera_make: Camera manufacturer
                - camera_model: Camera model
                - gps_latitude: GPS latitude (if available)
                - gps_longitude: GPS longitude (if available)
                - gps_altitude: GPS altitude in meters (if available)
                - orientation: Image orientation
                - width: Image width in pixels
                - height: Image height in pixels
                - flash: Whether flash was used
                - focal_length: Focal length in mm
                - iso: ISO speed rating
                - exposure_time: Exposure time in seconds
                - f_number: F-number (aperture)
                - software: Software used to process image
                - has_exif: Whether EXIF data was found
                - raw_exif: Dict of all raw EXIF tags (optional)
            
        Raises:
            ValueError: If neither image_bytes nor image_path provided
            RuntimeError: If metadata extraction fails
        """
        if image_bytes is None and image_path is None:
            raise ValueError("Either image_bytes or image_path must be provided")
        
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            # Open image
            if image_bytes:
                image = Image.open(BytesIO(image_bytes))
            else:
                image = Image.open(image_path)
            
            # Get basic image info
            metadata = {
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
                'has_exif': False
            }
            
            # Extract EXIF data
            exif_data = image.getexif()
            
            if exif_data is None or len(exif_data) == 0:
                logger.info(f"No EXIF data found in image")
                return metadata
            
            metadata['has_exif'] = True
            
            # Parse standard EXIF tags
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                exif_dict[tag_name] = value
            
            # Extract common fields
            metadata.update(self._extract_common_fields(exif_dict))
            
            # Extract GPS data if available
            gps_data = self._extract_gps_data(exif_data)
            if gps_data:
                metadata.update(gps_data)
            
            # Optionally include raw EXIF data
            metadata['raw_exif'] = exif_dict
            
            logger.debug(
                f"Extracted EXIF metadata: timestamp={metadata.get('timestamp')}, "
                f"camera={metadata.get('camera_make')} {metadata.get('camera_model')}"
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract EXIF metadata: {str(e)}")
            raise RuntimeError(f"EXIF extraction failed: {str(e)}") from e
    
    def _extract_common_fields(self, exif_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common EXIF fields.
        
        Args:
            exif_dict: Dictionary of EXIF tags
            
        Returns:
            Dictionary of extracted fields
        """
        fields = {}
        
        # Timestamp
        datetime_str = exif_dict.get('DateTime') or exif_dict.get('DateTimeOriginal')
        if datetime_str:
            try:
                # EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
                dt = datetime.strptime(str(datetime_str), "%Y:%m:%d %H:%M:%S")
                fields['timestamp'] = dt.isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse datetime: {datetime_str}, error: {e}")
                fields['timestamp'] = str(datetime_str)
        else:
            fields['timestamp'] = None
        
        # Camera info
        fields['camera_make'] = exif_dict.get('Make')
        fields['camera_model'] = exif_dict.get('Model')
        fields['software'] = exif_dict.get('Software')
        
        # Orientation
        orientation = exif_dict.get('Orientation')
        if orientation:
            fields['orientation'] = self._parse_orientation(orientation)
        else:
            fields['orientation'] = None
        
        # Camera settings
        fields['iso'] = exif_dict.get('ISOSpeedRatings')
        
        # Exposure time
        exposure_time = exif_dict.get('ExposureTime')
        if exposure_time:
            try:
                if isinstance(exposure_time, tuple):
                    fields['exposure_time'] = exposure_time[0] / exposure_time[1]
                else:
                    fields['exposure_time'] = float(exposure_time)
            except Exception:
                fields['exposure_time'] = str(exposure_time)
        else:
            fields['exposure_time'] = None
        
        # F-number
        f_number = exif_dict.get('FNumber')
        if f_number:
            try:
                if isinstance(f_number, tuple):
                    fields['f_number'] = f_number[0] / f_number[1]
                else:
                    fields['f_number'] = float(f_number)
            except Exception:
                fields['f_number'] = str(f_number)
        else:
            fields['f_number'] = None
        
        # Focal length
        focal_length = exif_dict.get('FocalLength')
        if focal_length:
            try:
                if isinstance(focal_length, tuple):
                    fields['focal_length'] = focal_length[0] / focal_length[1]
                else:
                    fields['focal_length'] = float(focal_length)
            except Exception:
                fields['focal_length'] = str(focal_length)
        else:
            fields['focal_length'] = None
        
        # Flash
        flash = exif_dict.get('Flash')
        if flash is not None:
            fields['flash'] = bool(flash & 1)  # Bit 0 indicates if flash fired
        else:
            fields['flash'] = None
        
        return fields
    
    def _extract_gps_data(self, exif_data) -> Optional[Dict[str, Any]]:
        """
        Extract GPS coordinates from EXIF data.
        
        Args:
            exif_data: EXIF data object
            
        Returns:
            Dictionary with GPS data or None if not available
        """
        try:
            from PIL.ExifTags import GPSTAGS
            
            # Get GPS IFD
            gps_ifd = exif_data.get_ifd(0x8825)
            
            if not gps_ifd:
                return None
            
            # Parse GPS tags
            gps_data = {}
            for tag_id, value in gps_ifd.items():
                tag_name = GPSTAGS.get(tag_id, tag_id)
                gps_data[tag_name] = value
            
            if not gps_data:
                return None
            
            # Extract coordinates
            result = {}
            
            # Latitude
            if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                lat = self._convert_to_degrees(gps_data['GPSLatitude'])
                if gps_data['GPSLatitudeRef'] == 'S':
                    lat = -lat
                result['gps_latitude'] = lat
            
            # Longitude
            if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                lon = self._convert_to_degrees(gps_data['GPSLongitude'])
                if gps_data['GPSLongitudeRef'] == 'W':
                    lon = -lon
                result['gps_longitude'] = lon
            
            # Altitude
            if 'GPSAltitude' in gps_data:
                altitude = gps_data['GPSAltitude']
                if isinstance(altitude, tuple):
                    result['gps_altitude'] = altitude[0] / altitude[1]
                else:
                    result['gps_altitude'] = float(altitude)
            
            # GPS timestamp
            if 'GPSDateStamp' in gps_data and 'GPSTimeStamp' in gps_data:
                try:
                    date_str = gps_data['GPSDateStamp']
                    time_tuple = gps_data['GPSTimeStamp']
                    
                    # Convert time tuple to string
                    hour = int(time_tuple[0])
                    minute = int(time_tuple[1])
                    second = int(time_tuple[2])
                    
                    datetime_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"
                    dt = datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")
                    result['gps_timestamp'] = dt.isoformat()
                except Exception as e:
                    logger.warning(f"Failed to parse GPS timestamp: {e}")
            
            return result if result else None
            
        except Exception as e:
            logger.warning(f"Failed to extract GPS data: {str(e)}")
            return None
    
    def _convert_to_degrees(self, value) -> float:
        """
        Convert GPS coordinates to degrees.
        
        Args:
            value: GPS coordinate tuple (degrees, minutes, seconds)
            
        Returns:
            Decimal degrees
        """
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        
        return d + (m / 60.0) + (s / 3600.0)
    
    def _parse_orientation(self, orientation: int) -> str:
        """
        Parse EXIF orientation value.
        
        Args:
            orientation: EXIF orientation value (1-8)
            
        Returns:
            Human-readable orientation string
        """
        orientations = {
            1: "Normal",
            2: "Mirrored horizontal",
            3: "Rotated 180",
            4: "Mirrored vertical",
            5: "Mirrored horizontal then rotated 90 CCW",
            6: "Rotated 90 CW",
            7: "Mirrored horizontal then rotated 90 CW",
            8: "Rotated 90 CCW"
        }
        
        return orientations.get(orientation, f"Unknown ({orientation})")
    
    @kernel_function(
        name="extract_timestamp",
        description=(
            "Extract just the timestamp from image EXIF data. "
            "Returns ISO format timestamp or None if not available."
        )
    )
    def extract_timestamp(
        self,
        image_bytes: bytes = None,
        image_path: str = None
    ) -> Optional[str]:
        """
        Extract only the timestamp from image EXIF data.
        
        Args:
            image_bytes: Raw image bytes (optional if image_path provided)
            image_path: Path to image file (optional if image_bytes provided)
            
        Returns:
            ISO format timestamp string or None
        """
        try:
            metadata = self.extract_metadata(
                image_bytes=image_bytes,
                image_path=image_path
            )
            return metadata.get('timestamp')
        except Exception as e:
            logger.warning(f"Failed to extract timestamp: {str(e)}")
            return None
    
    @kernel_function(
        name="extract_gps_coordinates",
        description=(
            "Extract GPS coordinates from image EXIF data. "
            "Returns latitude, longitude, and altitude if available."
        )
    )
    def extract_gps(
        self,
        image_bytes: bytes = None,
        image_path: str = None
    ) -> Dict[str, Optional[float]]:
        """
        Extract only GPS coordinates from image EXIF data.
        
        Args:
            image_bytes: Raw image bytes (optional if image_path provided)
            image_path: Path to image file (optional if image_bytes provided)
            
        Returns:
            Dictionary with gps_latitude, gps_longitude, gps_altitude
        """
        try:
            metadata = self.extract_metadata(
                image_bytes=image_bytes,
                image_path=image_path
            )
            
            return {
                'gps_latitude': metadata.get('gps_latitude'),
                'gps_longitude': metadata.get('gps_longitude'),
                'gps_altitude': metadata.get('gps_altitude')
            }
        except Exception as e:
            logger.warning(f"Failed to extract GPS data: {str(e)}")
            return {
                'gps_latitude': None,
                'gps_longitude': None,
                'gps_altitude': None
            }
