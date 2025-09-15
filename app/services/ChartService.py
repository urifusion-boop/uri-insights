from typing import Any, List, Dict


class ChartService:
    @staticmethod
    async def generate_chart_data(
        chart_type: str, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates structured data for a chart instead of JSX code.
        """

        labels = [item["label"] for item in data]
        values = [item["value"] for item in data]

        return {
            "status": "success",
            "chart_type": chart_type,  # Chart type (bar, line, pie, etc.)
            "data": [
                {"label": label, "value": value} for label, value in zip(labels, values)
            ],
            "x_axis_key": "label",  # X-axis key for frontend
            "y_axis_key": "value",  # Y-axis key for frontend
            "title": "Generated Chart",
            "subtitle": "AI-generated data visualization",
            "description": "This chart represents the insights extracted from the tracked data.",
        }
