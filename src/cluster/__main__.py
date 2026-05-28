import typer

from src.cluster.cluster import app as cluster_app
from src.cluster.tune import app as tune_app

app = typer.Typer()
app.add_typer(cluster_app, name="run")
app.add_typer(tune_app, name="tune")

if __name__ == "__main__":
    app()
