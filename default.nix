{
  lib,
  python3Packages,
  zenity,
}:
{
  aw-watcher-ask = python3Packages.buildPythonApplication {
    pname = "aw-watcher-ask";
    version = "unstable";

    # src = fetchFromGitHub {
    #   owner = "bcbernardo";
    #   repo = "aw-watcher-ask";
    #   rev = "7b09be0e28a3c3d9227af0782d756c48f9217191";
    #   sha256 = "sha256-MASwH9rP0GRcbq9AoZr52oWYV2v8q/zEQDz0UAWFouA=";
    # };
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
}
