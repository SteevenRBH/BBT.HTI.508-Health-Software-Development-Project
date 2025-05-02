import io
import base64
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.interpolate import make_interp_spline
from matplotlib.font_manager import FontProperties
import matplotlib.dates as m_dates
from datetime import timedelta, timezone


def wrap_text(text, max_length=20):
    """Utility function to wrap text to fit in legend"""
    # Split the text into words
    words = text.split()
    wrapped_text = []
    current_line = ""

    for word in words:
        # If the current line plus the word exceeds max_length, wrap to the next line
        if len(current_line) + len(word) + 1 > max_length:
            wrapped_text.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
    wrapped_text.append(current_line)

    return "\n".join(wrapped_text)

def create_combined_colormap(measurements_data, medication):
    # --- Combine the keys ---
    measurement_codes = list(measurements_data.keys())
    medication_codes = list(medication.keys())
    all_codes = measurement_codes + medication_codes  # Combined list of all codes

    # --- Create a colormap for the combined list of keys ---
    num_colors = len(all_codes)  # Number of required colors

    # Generate colors using the colormap
    available_colors = [plt.get_cmap("tab20c")(i / (num_colors - 1)) for i in range(num_colors)]  # Get evenly spaced colors

    # Create a color map dictionary (key -> color)
    color_map = {code: available_colors[i] for i, code in enumerate(all_codes)}

    return color_map

def normalize_datetime(dt):
    """Converts datetime to timezone-aware if it isn't already"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_data_date_limits(measurements_data, medication_data):
    """Get the minimum and maximum dates from all available data."""
    all_dates = []

    # Get dates from measurements
    for data in measurements_data.values():
        if data:
            all_dates.extend(normalize_datetime(date) for date in data.keys())

    # Get dates from medications
    for med_list in medication_data.values():
        for med in med_list:
            if med["date"]:
                all_dates.append(normalize_datetime(med["date"]))

    if not all_dates:
        return None, None

    # Add padding to the date range (8 days on each side)
    date_range = timedelta(days=8)
    min_date = min(all_dates) - date_range
    max_date = max(all_dates) + date_range

    return min_date, max_date

def plot_measurements(measurements_data, medication, cholest_ref_values=None, smooth=False, show_units=False, alt_date_limits=None):
    """
    Plots time series data for lab measurements with dual Y-axes and superimposes vertical lines for medications.
    Uses triangular markers for cholesterol and circular markers for glucose measurements.

    Parameters:
        measurements_data (dict): Mapping of measurement codes to date->data-point dictionaries.
        medication (dict): Mapping of medication codes to lists of dicts with 'date', 'name', 'dosage'.
        cholest_ref_values (dict, optional): Dictionary with dates as keys and [lower, upper] bounds as values.
        smooth (bool): If True, smoothens the data with splines before plotting.
        show_units (bool): If True, display units above each measurement point.
        alt_date_limits (list, optional): Two-element list specifying the x-axis date limits as [start_date, end_date].
    """
    # --- Setup ---
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()  # Create a second Y-axis
    
    # Configure date formatting
    locator = m_dates.AutoDateLocator()
    formatter = m_dates.ConciseDateFormatter(locator)
    ax1.xaxis.set_major_locator(locator)
    ax1.xaxis.set_major_formatter(formatter)
    
    # Add reference values shading if provided
    if cholest_ref_values:
        dates = sorted(cholest_ref_values.keys())
        lower_bounds = [cholest_ref_values[date][0] for date in dates]
        upper_bounds = [cholest_ref_values[date][1] for date in dates]
        
        # Get y-axis limits to extend the shading
        y_max = 10000  # Set a reasonable maximum for cholesterol values

        # Normal cholesterol range (below lower bound)
        ax1.fill_between(dates, 0 * len(dates), lower_bounds,
                         alpha=0.02, color='midnightblue')
        
        # Borderline range (reference values)
        ax1.fill_between(dates, lower_bounds, upper_bounds, 
                        alpha=0.2, color='orange')
        
        # High-cholesterol range (above upper bound)
        ax1.fill_between(dates, upper_bounds, [y_max] * len(dates),
                        alpha=0.2, color='red')
    
    color_map = create_combined_colormap(measurements_data, medication)

    measurement_labels_plotted = False
    cholesterol_lines = []
    glucose_lines = []

    # --- Plot Lab Measurements ---
    for code, data in measurements_data.items():
        if not data:
            continue

        dates = sorted(data.keys())
        values = [sum(entry["value"] for entry in data[date]) / len(data[date]) for date in dates]
        dates_numeric = np.array([date.timestamp() for date in dates])
        values = np.array(values)
        color = color_map[code]

        # Determine which axis and marker to use based on a measurement type
        is_cholesterol = "CHOLEST" in code.upper()
        ax = ax1 if is_cholesterol else ax2
        marker = '^' if is_cholesterol else 'o'
        line_collection = cholesterol_lines if is_cholesterol else glucose_lines

        if len(dates) > 2 and smooth:
            spline = make_interp_spline(dates_numeric, values, k=2)
            smooth_dates_numeric = np.linspace(dates_numeric.min(), dates_numeric.max(), 300)
            smooth_values = spline(smooth_dates_numeric)
            smooth_dates = [datetime.fromtimestamp(d) for d in smooth_dates_numeric]
            line, = ax.plot(smooth_dates, smooth_values, linestyle='-', color=color)
        else:
            line, = ax.plot(dates, values, linestyle='-', color=color)

        scatter = ax.scatter(dates, values, color=color, marker=marker, s=100, zorder=3, label=code)
        line_collection.append((line, scatter))
        measurement_labels_plotted = True

        if show_units:
            units = [data[date][0]["unit"] for date in dates]
            for i, txt in enumerate(units):
                ax.annotate(txt, (dates[i], values[i]), textcoords="offset points", xytext=(0, 5), ha='center')

    # --- Plot Medications ---
    med_records = []
    for code in list(medication.keys()):
        records = medication[code]
        for med in records:
            if med["date"]:
                med_records.append(med | {"code": code})

    med_for_legend = {}
    for med in med_records:
        date = med["date"]
        name = med["name"]
        code = med["code"]
        color = color_map[code]

        ax1.axvline(date, linestyle='--', color=color)
        med_for_legend[name] = color

    # --- Legends ---
    bold_font = FontProperties(weight='bold')

    # Wrap medication names
    wrapped_med_names = {wrap_text(name): color for name, color in med_for_legend.items()}

    # Create reference values legend if they are provided
    if cholest_ref_values:
        ref_legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.2,
                          label=wrap_text('High')),
            plt.Rectangle((0, 0), 1, 1, facecolor='orange', alpha=0.2, 
                        label=wrap_text('Borderline high')),
            plt.Rectangle((0, 0), 1, 1, facecolor='midnightblue', alpha=0.02,
                          label=wrap_text('Normal'))
        ]
        ref_legend = ax1.legend(handles=ref_legend_elements, 
                              title=wrap_text("Reference values"),
                              bbox_to_anchor=(1.1, 0.5), loc="center left",
                              title_fontproperties=bold_font, ncol=1)
        ax1.add_artist(ref_legend)

    # Create combined legend for measurements
    if measurement_labels_plotted:
        legend_elements = []
        
        # Add cholesterol measurements to legend
        for _, scatter in cholesterol_lines:
            legend_elements.append(plt.Line2D([0], [0], marker='^', color='none',
                                            markerfacecolor=scatter.get_facecolor()[0],
                                            markeredgecolor=scatter.get_edgecolor()[0],
                                            markersize=10, label=scatter.get_label()))

        # Add glucose measurements to legend
        for _, scatter in glucose_lines:
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='none',
                                            markerfacecolor=scatter.get_facecolor()[0],
                                            markeredgecolor=scatter.get_edgecolor()[0],
                                            markersize=10, label=scatter.get_label()))

        measurement_legend = ax1.legend(handles=legend_elements, title="Measurements",
                                      bbox_to_anchor=(1.1, 1), loc="upper left",
                                      title_fontproperties=bold_font, ncol=1)
        if med_for_legend:
            ax1.add_artist(measurement_legend)

    # Add medication legend if any medication data exists
    if med_for_legend:
        med_handles = [plt.Line2D([0], [0], color=color, linestyle='--', label=name)
                      for name, color in wrapped_med_names.items()]
        med_legend = ax1.legend(handles=med_handles, title="Medications",
                               bbox_to_anchor=(1.1, 0), loc="lower left",
                               title_fontproperties=bold_font, ncol=1)

    # --- Final Touches ---
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Cholesterol Measurement Value (mg/dL)", color='black')
    ax2.set_ylabel("Glucose Measurement Value (mg/dL)", color='black')

    # Get all dates and values to determine axis limits
    all_dates = []
    cholesterol_values = []
    glucose_values = []

    # Collect cholesterol data points
    for line, scatter in cholesterol_lines:
        offsets = scatter.get_offsets()
        if len(offsets) > 0:
            dates = m_dates.num2date(offsets[:, 0])
            all_dates.extend(normalize_datetime(d) for d in dates)
            cholesterol_values.extend(offsets[:, 1])

    # Collect glucose data points
    for line, scatter in glucose_lines:
        offsets = scatter.get_offsets()
        if len(offsets) > 0:
            dates = m_dates.num2date(offsets[:, 0])
            all_dates.extend(normalize_datetime(d) for d in dates)
            glucose_values.extend(offsets[:, 1])

    # Collect medication dates
    for med in med_records:
        if med["date"]:
            all_dates.append(normalize_datetime(med["date"]))

    # --- Adjust x-axis limits based on `alt_date_limits` ---
    if alt_date_limits and len(alt_date_limits) == 2:
        ax1.set_xlim(alt_date_limits[0], alt_date_limits[1])
    else:
        # The default behavior remains unchanged if `alt_date_limits` is not provided
        if all_dates:
            # Add padding to the date range (8 days on each side)
            date_range = timedelta(days=8)
            x_min = min(all_dates) - date_range
            x_max = max(all_dates) + date_range
            ax1.set_xlim(x_min, x_max)

    # Adjust axes limits if there is data
    if cholesterol_values:
        chol_min = min(cholesterol_values) * 0.9
        chol_max = max(cholesterol_values) * 1.1
    else:
        chol_min = 0
        chol_max = 300

    if glucose_values:
        glucose_min = min(glucose_values) * 0.9
        glucose_max = max(glucose_values) * 1.1
    else:
        glucose_min = 0
        glucose_max = 200

    if cholest_ref_values:
        # Define mapping: cholesterol → glucose
        m = (125 - 100) / (239 - 199)
        b = 125 - m * 239

        # Provisional cholesterol limits
        y_min = chol_min
        y_max = chol_max

        # Compute corresponding glucose limits from provisional cholesterol limits
        gluc_min_mapped = m * y_min + b
        gluc_max_mapped = m * y_max + b

        # Expand cholesterol limits if needed to fit glucose data
        if glucose_min < gluc_min_mapped:
            y_min = (glucose_min - b) / m
        if glucose_max > gluc_max_mapped:
            y_max = (glucose_max - b) / m

        # Set final axis limits
        ax1.set_ylim(y_min, y_max)
        ax2.set_ylim(m * y_min + b, m * y_max + b)

    else:
        # Set independent limits based on data only
        ax1.set_ylim(chol_min, chol_max)
        ax2.set_ylim(glucose_min, glucose_max)

    # Annotate medications
    used_annotations = set()
    for med in med_records:
        date = med["date"]
        name = med["name"]
        if (date, name) not in used_annotations:
            ax1.annotate(name, xy=(date, ax1.get_ylim()[0]), xytext=(0, 10),
                         textcoords="offset points", ha='center', va='bottom',
                         fontsize=8, rotation=90, color='black',
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color_map[med["code"]], lw=0.8))
            used_annotations.add((date, name))

    ax1.tick_params(axis='x', rotation=30)
    ax1.set_title("Cholesterol and Glucose Measurements Over Time", weight='bold')
    ax1.grid(True)
    plt.tight_layout()
    return fig

def generate_plot_uri(measurements, medications, cholest_ref_values=None, smooth=False, show_units=False, alt_date_limits=None):
    """
    Generates a plot URI (base64 encoded image) for the given measurements and medications data.

    This function checks whether there is any data to plot for the given measurements and medications.
    If there is data, it generates a plot using matplotlib, encodes the plot into a base64 string,
    and returns the base64-encoded image URI. If there is no data to plot, it returns None and
    a flag indicating that no data was found.

    :param measurements: Dictionary containing measurement data with codes as keys and lists as values.
    :param medications: Dictionary containing medication data with codes as keys and lists as values.
    :param cholest_ref_values: Dictionary with dates as keys and [lower, upper] bounds as values.
    :param smooth: Bool, if True, smoothens the data with splines before plotting.
    :param show_units: Bool, if True, displays units above each measurement point.
    :param alt_date_limits: List of two datetime objects specifying the x-axis date limits.
    :return: str: The base64 encoded image URI of the plot or None if no data to plot.
    """

    # Check if there is any data in the measurements or medications
    if not any(measurements[code] for code in measurements) and not any(medications[code] for code in medications):
        # If both measurements and medications have no data, set image_uri to None
        image_uri = None  # No plot to display
    else:
        # Create a buffer to hold the plot image
        buf = io.BytesIO()

        # Generate the plot using the plot_measurements function (imported from tools.py)
        plot_measurements(measurements, medications, cholest_ref_values, smooth, show_units, alt_date_limits)

        # Save the plot to the buffer in PNG format
        plt.savefig(buf, format='png', bbox_inches='tight')

        # Close the plot to free up resources
        plt.close()

        # Encode the plot in base64 format to be used in HTML
        buf.seek(0)  # Move to the start of the buffer
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')  # Encode as a base64 string
        image_uri = f"data:image/png;base64,{image_base64}"  # Construct the data URI for embedding

    # Return the image URI and the flag indicating if there is data to plot
    return image_uri