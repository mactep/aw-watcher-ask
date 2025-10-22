{
  description = "ActivityWatch watcher that asks the user questions";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/c407032be28ca2236f45c49cfb2b8b3885294f7f";
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
      in
      {
        packages = {
          default = (pkgs.callPackage ./default.nix { }).aw-watcher-ask;
        };
      }
    );
}
