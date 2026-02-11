{
  description = "ActivityWatch watcher that asks the user questions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        aw-watcher-ask = (pkgs.callPackage ./default.nix { inherit pkgs; }).aw-watcher-ask;
      in
      {
        packages = {
          aw-watcher-ask = aw-watcher-ask;
          default = aw-watcher-ask;
          aw-watcher-ask-export = (pkgs.callPackage ./default.nix { inherit pkgs; }).aw-watcher-ask-export;
        };

        devShells = {
          default = pkgs.mkShell {
            inputsFrom = [ aw-watcher-ask ];
            packages = [
              pkgs.poetry
              pkgs.python3Packages.pytest
              pkgs.python3Packages.pip
            ];
            shellHook = ''
              python3 -m venv .venv
              source .venv/bin/activate
            '';
          };
        };
      }
    );
}
