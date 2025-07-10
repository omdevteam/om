from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self


class Hdf5Compression(Enum):
    gzip = "gzip"
    bitshuffle_with_zstd = "bitshuffle_with_zstd"
    none = None


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",  # Allows extra attributes during validation
    )


class OmParameters(CustomBaseModel):
    parallelization_layer: str
    data_retrieval_layer: str
    processing_layer: str
    source: str = Field(default="")
    configuration_file: Path = Field(default="")


class DataSourceParameters(CustomBaseModel):
    type: str
    model_config = ConfigDict(extra="allow")


class DataRetrievalLayerParameters(CustomBaseModel):
    # asapo
    asapo_url: Optional[str] = Field(default=None)
    asapo_path: Optional[str] = Field(default=None)
    asapo_data_source: Optional[str] = Field(default=None)
    asapo_has_filesystem: Optional[bool] = Field(default=None)
    asapo_token: Optional[str] = Field(default=None)
    asapo_group_id: str = Field(default="default_om_group")
    # http
    buffer_size: Optional[int] = Field(default=None)
    # psana
    psana_calibration_directory: Optional[str] = Field(default=None)
    # all
    data_sources: dict[str, DataSourceParameters]
    node_pool_size: int = Field(default=0)


class Peakfinder8PeakDetectionParameters(CustomBaseModel):
    max_num_peaks: int
    adc_threshold: float
    minimum_snr: float
    min_pixel_count: int
    max_pixel_count: int
    local_bg_radius: int
    min_res: int
    max_res: int
    fast_mode: bool = Field(default=False)
    num_pixel_per_bin_in_radial_statistics: int = Field(default=100)
    bad_pixel_map_filename: Optional[Path] = Field(default=None)
    bad_pixel_map_hdf5_path: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def check_hd5_path(self) -> Self:
        """ """
        if (
            self.bad_pixel_map_filename is not None
            and self.bad_pixel_map_hdf5_path is None
        ):
            raise ValueError(
                "If the bad_pixel_map_filename parameter is specified for a specific "
                "detector, the bad_pixel_map_hdf5_path parameters must also be "
                "provided"
            )
        return self


class RadialProfileParameters(CustomBaseModel):
    bad_pixel_map_filename: Optional[str] = Field(default=None)
    bad_pixel_map_hdf5_path: Optional[str] = Field(default=None)
    radius_bin_size: float

    @model_validator(mode="after")
    def check_hd5_path(self) -> Self:
        if (
            self.bad_pixel_map_filename is not None
            and self.bad_pixel_map_hdf5_path is None
        ):
            raise ValueError(
                "If the bad_pixel_map_filename parameter is specified, "
                "the bad_pixel_map_hdf5_path must also be provided"
            )
        return self


class BinningParameters(CustomBaseModel):
    bin_size: int
    min_good_pix_count: Optional[int] = Field(default=None)
    bad_pixel_value: Optional[Union[int, float]] = Field(default=None)
    bad_pixel_map_filename: Optional[str] = Field(default=None)
    bad_pixel_map_hdf5_path: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def check_hd5_path(self) -> Self:
        if (
            self.bad_pixel_map_filename is not None
            and self.bad_pixel_map_hdf5_path is None
        ):
            raise ValueError(
                "If the bad_pixel_map_filename parameter is specified, "
                "the bad_pixel_map_hdf5_path must also be provided"
            )
        return self


class XesParameters(CustomBaseModel):
    intensity_threshold: Optional[float] = Field(default=None)
    rotation_in_degrees: float
    min_row_in_pix_for_integration: int
    max_row_in_pix_for_integration: int


class CheetahParameters(CustomBaseModel):
    processed_directory: str
    processed_filename_prefix: str = Field(default="processed")
    processed_filename_extension: str = Field(default="h5")
    hdf5_fields: Dict[str, str]
    hdf5_file_data_type: str
    hdf5_file_compression: Hdf5Compression = Field(default=Hdf5Compression.none)
    hdf5_file_gzip_compression_level: int = Field(default=4)
    hdf5_file_zstd_compression_level: int = Field(default=3)
    hdf5_file_compression_shuffle: bool = Field(default=False)
    hdf5_file_max_num_peaks: int = Field(default=1024)
    class_sums_sending_interval: int = Field(default=-1)
    write_class_sums: bool
    class_sums_update_interval: int
    status_file_update_interval: int
    responding_url: Optional[str] = Field(default=None)
    external_data_request_list_size: int = Field(default=20)

    @model_validator(mode="after")
    def check_sums_update_interval(self) -> Self:
        if self.write_class_sums is True and self.class_sums_update_interval is -1:
            raise ValueError(
                "If writing of the class sums is requested from Cheetah, the following"
                "entry must be present in the cheetah section of the configuration"
                "file:  class_sums_update_interval "
            )
        return self

    @field_validator("status_file_update_interval")
    def check_status_file_update_interval(cls: Self, v: int) -> int:
        if v < 1:
            raise ValueError(
                "The following entry in the configuration file must have a value of 1 "
                "or higher: cheetah/status_file_update_interval"
            )
        return v


class CrystallographyParameters(CustomBaseModel):
    peakfinding_algorithm: str = Field(default="peakfinder8")
    min_num_peaks_for_hit: int
    max_num_peaks_for_hit: int
    peakogram_intensity_bin_size: float = Field(default=100.0)
    peakogram_radius_bin_size: float = Field(default=5.0)
    running_average_window_size: int
    post_processing_binning: bool = Field(default=False)
    pump_probe_experiment: bool = Field(default=False)
    geometry_file: str
    geometry_is_optimized: bool = Field(default=False)
    speed_report_interval: int
    data_broadcast_url: Optional[str] = Field(default=None)
    responding_url: Optional[str] = Field(default=None)
    external_data_request_list_size: int = Field(default=20)
    data_broadcast_interval: int
    hit_frame_sending_interval: Optional[int] = Field(default=None)
    non_hit_frame_sending_interval: Optional[int] = Field(default=None)


class MonitorParameters(CustomBaseModel):
    om: OmParameters
    data_retrieval_layer: DataRetrievalLayerParameters
    peakfinder8_peak_detection: Optional[Peakfinder8PeakDetectionParameters] = Field(
        default=None
    )
    radial_profile: Optional[RadialProfileParameters] = Field(default=None)
    binning: Optional[BinningParameters] = Field(default=None)
    crystallography: Optional[CrystallographyParameters] = Field(default=None)
    xes: Optional[XesParameters] = Field(default=None)
    cheetah: Optional[CheetahParameters] = Field(default=None)

    @model_validator(mode="after")
    def check_peakfinder8_peak_detection_parameters(self) -> Self:
        if (
            self.crystallography is not None
            and self.crystallography.peakfinding_algorithm == "peakfinder8"
            and self.peakfinder8_peak_detection is None
        ):
            raise ValueError(
                "When using peakfinder8 crystallography peak detection, the following "
                "section must be present in OM's configuration parameters: "
                "peakfinder8_peak_detection"
            )
        return self

    @model_validator(mode="after")
    def check_binning_parameters(self) -> Self:
        if (
            self.crystallography is not None
            and self.crystallography.post_processing_binning is True
            and self.binning is None
        ):
            raise ValueError(
                "When post processing binning is requested, the following section must "
                "be present in OM's configuration parameters: binning"
            )
        return self
