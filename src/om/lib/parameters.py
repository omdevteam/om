from enum import Enum
from pathlib import Path
from typing import Literal
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class RoiBinSzCompressorParameters(CustomBaseModel):
    compressor: Literal["qoz", "sz3"] = Field(
        "qoz", description='Compression algorithm ("qoz" or "sz3")'
    )
    abs_error: float = Field(10.0, description="Absolute error bound")
    bin_size: int = Field(2, description="Bin size")
    roi_window_size: int = Field(
        9,
        description="Default window size",
    )
    mask: str | bool | None = None


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


class RadialProfileParameters(CustomBaseModel):
    speed_report_interval: int
    data_broadcast_interval: int
    hit_frame_sending_interval: int
    non_hit_frame_sending_interval: int
    data_broadcast_url: str | None = None
    radius_bin_size: int
    geometry_file: str
    post_processing_binning: bool = False
    bad_pixel_map_filename: str | None = None
    bad_pixel_map_hdf5_path: str | None = None
    running_average_window_size: int
    num_radials_to_send: int
    num_hits_in_cum_radial_avg: int
    total_intensity_jet_threshold: float = -1.0
    background_subtraction: bool = False
    background_profile_filename: str = ""
    background_profile_hdf5_path: str = ""
    background_subtraction_min_fit_bin: int = -1
    background_subtraction_max_fit_bin: int = -1
    sample_detection: bool = True
    minimum_roi1_to_roi2_intensity_ratio_for_sample: float = -1.0
    maximum_roi1_to_roi2_intensity_ratio_for_sample: float = -1.0
    estimate_particle_size: bool = False
    size_estimation_method: Literal["guinier", "sphere", "peak"] = "guinier"
    roi1_qmin: float = -1.0
    roi1_qmax: float = -1.0
    roi2_qmin: float = -1.0
    roi2_qmax: float = -1.0
    guinier_qmin: float = -1.0
    guinier_qmax: float = -1.0

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

    @model_validator(mode="after")
    def check_background_subtraction(self) -> Self:
        if self.background_subtraction is True and (
            self.background_profile_filename == ""
            or self.background_profile_hdf5_path == ""
            or self.background_subtraction_min_fit_bin == -1
            or self.background_subtraction_max_fit_bin == -1
        ):
            raise ValueError(
                "When background subtraction is requested, the following entries "
                "entry must be present in the swaxs section of the configuration "
                "file: background_profile_filename, background_profile_hdf5_path, "
                "background_subtraction_min_fit_bin, background_subtraction_max_fit_bin"
            )
        return self

    @model_validator(mode="after")
    def check_sample_detection(self) -> Self:
        if self.sample_detection is True and (
            self.total_intensity_jet_threshold == -1
            or self.roi1_qmin == -1.0
            or self.roi1_qmax == -1.0
            or self.roi2_qmin == -1.0
            or self.roi2_qmax == -1.0
            or self.minimum_roi1_to_roi2_intensity_ratio_for_sample == -1.0
            or self.maximum_roi1_to_roi2_intensity_ratio_for_sample == -1.0
        ):
            raise ValueError(
                "When background subtraction is requested, the following entries "
                "entry must be present in the swaxs section of the configuration "
                "file: total_intensity_jet_threshold, roi1_qmin, roi1_qman, roi2_qmin, "
                "roi2_max, minimum_roi1_to_roi2_intensity_ratio_for_sample, "
                "maximum_roi1_to_roi2_intensity_ratio_for_sample"
            )
        return self

    @model_validator(mode="after")
    def check_particle_size_estimation(self) -> Self:
        if (
            self.estimate_particle_size is True
            and self.size_estimation_method == "guinier"
            and (self.guinier_qmin == 1 and self.guinier_qmax == 1)
        ):
            raise ValueError(
                "When background subtraction is requested, the following entries "
                "entry must be present in the swaxs section of the configuration "
                "file: total_intensity_jet_threshold, roi1_qmin, roi1_qman, roi2_qmin, "
                "roi2_max, minimum_roi1_to_roi2_intensity_ratio_for_sample, "
                "maximum_roi1_to_roi2_intensity_ratio_for_sample"
            )
        return self


class CheetahParameters(CustomBaseModel):
    processed_directory: str
    processed_filename_prefix: str = "processed"
    processed_filename_extension: str = "h5"
    hdf5_fields: dict[str, str]
    hdf5_file_data_type: str | None = None
    hdf5_file_compression: Hdf5Compression = Hdf5Compression.none
    hdf5_file_gzip_compression_level: int = 4
    hdf5_file_zstd_compression_level: int = 3
    hdf5_file_compression_shuffle: bool = False
    hdf5_file_max_num_peaks: int = 1024
    write_class_sums: bool
    class_sums_sending_interval: int = -1
    class_sums_update_interval: int
    class_sums_filename_prefix: str = "sums"
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
    hit_frame_sending_interval: int = 0
    non_hit_frame_sending_interval: int = 0


class DataCompressionParameters(CustomBaseModel):
    run_compression: bool = False
    backend: Literal["roibinsz"] | None = None
    compression_parameters: RoiBinSzCompressorParameters | None = None

    @model_validator(mode="after")
    def check_backend_matches_parameters(self) -> Self:
        if self.run_compression:
            if self.backend == "roibinsz":
                if not isinstance(
                    self.compression_parameters, RoiBinSzCompressorParameters
                ):
                    raise ValueError(
                        "For the libpressio compression backend you must use a "
                        "SZCompressorParameters for `compression_parameters`."
                    )
        return self


class MonitorParameters(CustomBaseModel):
    om: OmParameters
    data_retrieval_layer: DataRetrievalLayerParameters
    peakfinder8_peak_detection: Peakfinder8PeakDetectionParameters | None = None
    radial_profile: RadialProfileParameters | None = None
    binning: BinningParameters | None = None
    crystallography: CrystallographyParameters | None = None
    xes: XesParameters | None = None
    cheetah: CheetahParameters | None = None
    compression: DataCompressionParameters | None = None

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
