import * as anchor from "@project-serum/anchor";
import { Program } from "@project-serum/anchor";
import { MarinadeRsSdkTest } from "../target/types/marinade_rs_sdk_test";

describe("marinade-rs-sdk-test", () => {
  // Configure the client to use the local cluster.
  anchor.setProvider(anchor.AnchorProvider.env());

  const program = anchor.workspace.MarinadeRsSdkTest as Program<MarinadeRsSdkTest>;

  it("Is initialized!", async () => {
    // Add your test here.
    const tx = await program.methods.initialize().rpc();
    console.log("Your transaction signature", tx);
  });
});
