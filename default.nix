{
  lib,
  pkgs,
  python3Packages,
  zenity,
}:
{
  aw-watcher-ask = python3Packages.buildPythonApplication {
    pname = "aw-watcher-ask";
    version = "unstable";

    src = ./.;

    pyproject = true;
    nativeBuildInputs = [ python3Packages.poetry-core ];

    propagatedBuildInputs =
      with python3Packages;
      [
        aw-client
        croniter
        loguru
        typer
        unidecode
      ]
      ++ [
        zenity
      ];

    pythonImportsCheck = [ "aw_watcher_ask" ];

    meta = with lib; {
      description = "An ActivityWatch watcher to pose questions to the user and record her answers";
      homepage = "https://github.com/ActivityWatch/aw-watcher-ask";
      mainProgram = "aw-watcher-ask";
      license = licenses.mit;
    };
  };

  aw-watcher-ask-export = let
    pythonEnv = python3Packages.python.withPackages (p: with p; [
      requests
      typer
    ]);
  in
    pkgs.writeShellApplication {
      name = "export_visualization";
      runtimeInputs = [ pythonEnv ];
      text = ''exec python3 ${./scripts/export_visualization.py} "$@"'';
      meta = with lib; {
        description = "Export ActivityWatch aw-watcher-ask data to a static HTML visualization";
        homepage = "https://github.com/ActivityWatch/aw-watcher-ask";
        license = licenses.mit;
      };
    };
}
