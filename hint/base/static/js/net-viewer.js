var plot_network = function(data) {
    var cy = cytoscape({
        container: document.getElementById("cy"), // container to render in
        elements: data,
        style: [ // the stylesheet for the graph
            {
                selector: "node",
                style: {
                    "background-color": "#666",
                    "label": "data(id)",
                    "background-color": "data(c)",
                },
            },
            {
                selector: "edge",
                style: {
                    "width": 3,
                    "line-color": "data(c)",
                    "curve-style": "bezier"
                },
            },
        ],
        layout: {
            name: "circle",
            rows: 1
        },
    });
}
