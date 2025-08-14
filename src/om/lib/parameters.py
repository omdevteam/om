from enum import Enum
from pathlib import Path
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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
    source: str = ""
    configuration_file: Path = Path("")


class DataSourceParameters(CustomBaseModel):
    type: str
    model_config = ConfigDict(extra="allow")


class DataRetrievalLayerParameters(CustomBaseModel):
    # asapo
    asapo_url: str | None = None
    asapo_path: str | None = None
    asapo_data_source: str | None = None
    asapo_has_filesystem: bool | None = None
    asapo_token: str | None = None
    asapo_group_id: str = "default_om_group"
    # http
    buffer_size: int | None = None
    # psana
    psana_calibration_directory: str | None = None
    # all
    data_sources: dict[str, DataSourceParameters]
    node_pool_size: int = 0


class Peakfinder8PeakDetectionParameters(CustomBaseModel):
    max_num_peaks: int
    adc_threshold: float
    minimum_snr: float
    min_pixel_count: int
    max_pixel_count: int
    local_bg_radius: int
    min_res: int
    max_res: int
    fast_mode: bool = False
    num_pixel_per_bin_in_radial_statistics: int = 100
    bad_pixel_map_filename: Path | None = None
    bad_pixel_map_hdf5_path: str | None = None

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
    bad_pixel_map_filename: str | None = None
    bad_pixel_map_hdf5_path: str | None = None
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
    min_good_pix_count: int | None = None
    bad_pixel_value: int | float | None = None
    bad_pixel_map_filename: str | None = None
    bad_pixel_map_hdf5_path: str | None = None

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
    intensity_threshold: float | None = None
    rotation_in_degrees: float
    geometry_file: str
    data_broadcast_url: str | None = None
    data_broadcast_interval: int
    time_resolved: bool = False
    min_row_in_pix_for_integration: int
    max_row_in_pix_for_integration: int
    running_average_window_size: int
    speed_report_interval: int
    hit_frame_sending_interval: int | None = None
    non_hit_frame_sending_interval: int | None = None


class CheetahParameters(CustomBaseModel):
    processed_directory: str
    processed_filename_prefix: str = "processed"
    processed_filename_extension: str = "h5"
    hdf5_fields: dict[str, str]
    hdf5_file_data_type: str
    hdf5_file_compression: Hdf5Compression = Hdf5Compression.none
    hdf5_file_gzip_compression_level: int = 4
    hdf5_file_zstd_compression_level: int = 3
    hdf5_file_compression_shuffle: bool = False
    hdf5_file_max_num_peaks: int = 1024
    class_sums_sending_interval: int = -1
    write_class_sums: bool
    class_sums_update_interval: int
    status_file_update_interval: int
    responding_url: str | None = None
    external_data_request_list_size: int = 20

    @model_validator(mode="after")
    def check_sums_update_interval(self) -> Self:
        if self.write_class_sums is True and self.class_sums_update_interval == -1:
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
    peakfinding_algorithm: str = "peakfinder8"
    min_num_peaks_for_hit: int
    max_num_peaks_for_hit: int
    peakogram_intensity_bin_size: float = 100.0
    peakogram_radius_bin_size: float = 5.0
    running_average_window_size: int
    post_processing_binning: bool = False
    pump_probe_experiment: bool = False
    geometry_file: str
    geometry_is_optimized: bool = False
    speed_report_interval: int
    data_broadcast_url: str | None = None
    responding_url: str | None = None
    external_data_request_list_size: int = 20
    data_broadcast_interval: int
    hit_frame_sending_interval: int | None = None
    non_hit_frame_sending_interval: int | None = None


class MonitorParameters(CustomBaseModel):
    om: OmParameters
    data_retrieval_layer: DataRetrievalLayerParameters
    peakfinder8_peak_detection: Peakfinder8PeakDetectionParameters | None = None
    radial_profile: RadialProfileParameters | None = None
    binning: BinningParameters | None = None
    crystallography: CrystallographyParameters | None = None
    xes: XesParameters | None = None
    cheetah: CheetahParameters | None = None

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
